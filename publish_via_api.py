#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub REST API 发布 guoxue-jianji-oss，不依赖 git push / gh CLI。

适用场景：本机代理只放行 api.github.com，github.com 被阻断（CONNECT 502）时，
git push 不可用，但 Git Data API 仍能完整创建仓库内容。

用法（任选一种提供 token）：
    GITHUB_TOKEN=ghp_xxx python3 publish_via_api.py [repo-name] [--private]
    或把 token 单独一行写入 ~/.config/guoxue-jianji/token，然后：
    python3 publish_via_api.py [repo-name]

Token 需要：目标仓库的 Contents 读写 + Administration（创建仓库用 classic PAT
需 repo scope；fine-grained PAT 需对该账号下仓库有写权限）。
把 token 放文件可避免它出现在聊天记录里；用完建议在 GitHub 设置中撤销。
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.github.com"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guoxue-jianji-oss")


def _read_token_file():
    """可选：从本地文件读 token，避免令牌出现在聊天记录中。"""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.expanduser("~/.config/guoxue-jianji/token"),
              os.path.join(here, ".github_token")):
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                return fh.read().strip() or None
    return None


TOKEN = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
         or _read_token_file())
REPO = next((a for a in sys.argv[1:] if not a.startswith("--")), "guoxue-jianji")
PRIVATE = "--private" in sys.argv
DESCRIPTION = "国学剪辑 · 古籍情景演绎竖屏短视频合成流水线（WorkBuddy Skill）"
COMMIT_MSG = ("Initial release: 国学剪辑 / Guoxue Editing\n\n"
              "古籍情景演绎竖屏短视频合成流水线：edge-tts 双音色配音、"
              "Wav2Lip 固定框对口型、PIL 灵动思考弹窗、字幕与片尾免责。\n\n"
              "含四集示例 spec 与关键帧预览。权重不入库，由 setup_env.sh 按需下载。\n"
              "许可 CC BY-NC-SA 4.0；第三方组件见 THIRD_PARTY.md。")


def req(method, path, payload=None, timeout=90):
    url = API + path
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("X-GitHub-Api-Version", "2022-11-28")
    r.add_header("Content-Type", "application/json")
    r.add_header("User-Agent", "guoxue-jianji-publisher")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError("%s %s -> HTTP %d: %s" % (method, path, e.code, detail)) from None


def main():
    if not TOKEN:
        sys.exit("缺少 GITHUB_TOKEN：请先设置环境变量（或改用 publish-github.sh）")
    if not os.path.isdir(ROOT):
        sys.exit("找不到发布目录：" + ROOT)

    me = req("GET", "/user")
    owner = me["login"]
    print("== 认证账号：%s" % owner)

    # 1) 创建仓库；若已存在（或细粒度 PAT 无建仓权限）则验证后复用
    base = "/repos/%s/%s" % (owner, REPO)
    created = False
    try:
        req("POST", "/user/repos", {
            "name": REPO, "description": DESCRIPTION,
            "private": PRIVATE, "has_issues": True, "has_wiki": False,
            "auto_init": False,
        })
        created = True
        print("== 已创建仓库 %s/%s (%s)" % (owner, REPO, "private" if PRIVATE else "public"))
    except RuntimeError as e:
        # 422=同名已存在；403/404=细粒度 PAT 不允许建仓，需用户预先在网页建好
        if not any(code in str(e) for code in ("422", "403", "404")):
            raise
        try:
            req("GET", base)
        except RuntimeError:
            raise RuntimeError(
                "无法创建仓库，且 %s/%s 不存在。请改用 classic PAT（repo scope），"
                "或先在 GitHub 网页手动创建空仓库 %s 后重试。原始错误：%s"
                % (owner, REPO, REPO, e)) from None
        print("== 复用已有仓库 %s/%s" % (owner, REPO))
    if created:
        # 新建仓库需要一小段时间完成初始化，确认可读后再写
        for _ in range(10):
            try:
                req("GET", base)
                break
            except RuntimeError:
                time.sleep(1)

    # 2) 收集待提交文件（沿用 git 已暂存的清单，自动遵守 .gitignore）
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    files = [f for f in files if f]
    print("== 待上传文件：%d 个" % len(files))
    total = sum(os.path.getsize(os.path.join(ROOT, f)) for f in files)
    print("== 原始体积：%.1f MB" % (total / 1048576))

    def blob(item):
        path = os.path.join(ROOT, item)
        with open(path, "rb") as fh:
            content = base64.b64encode(fh.read()).decode("ascii")
        mode = "100755" if os.stat(path).st_mode & 0o111 else "100644"
        last = None
        for attempt in range(3):
            try:
                res = req("POST", base + "/git/blobs",
                          {"content": content, "encoding": "base64"})
                return {"path": item, "mode": mode, "type": "blob", "sha": res["sha"]}
            except RuntimeError as e:
                last = e
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("blob 上传失败 %s：%s" % (item, last)) from None

    # 3) 并发创建 blob
    tree, done = [], 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(blob, f): f for f in files}
        for fut in as_completed(futures):
            tree.append(fut.result())
            done += 1
            if done % 10 == 0 or done == len(files):
                print("   blob %d/%d" % (done, len(files)), flush=True)
    tree.sort(key=lambda x: x["path"])

    # 4) tree -> commit -> ref
    tree_sha = req("POST", base + "/git/trees", {"tree": tree})["sha"]
    parents = []
    try:
        head = req("GET", base + "/git/ref/heads/main")
        parents = [head["object"]["sha"]]
    except RuntimeError:
        pass
    commit_sha = req("POST", base + "/git/commits",
                     {"message": COMMIT_MSG, "tree": tree_sha,
                      "parents": parents})["sha"]
    try:
        req("PATCH", base + "/git/refs/heads/main", {"sha": commit_sha, "force": False})
    except RuntimeError:
        req("POST", base + "/git/refs", {"ref": "refs/heads/main", "sha": commit_sha})

    print("== 完成：https://github.com/%s/%s" % (owner, REPO))
    print("   commit %s / %d files" % (commit_sha[:8], len(files)))


if __name__ == "__main__":
    main()
