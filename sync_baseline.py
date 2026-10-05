#!/usr/bin/env python3
"""Linux port of tools/sync_baseline.ps1 + tools/gen_md5s.ps1.

Usage (from the project root):
    python3 tools/sync_baseline.py
    python3 tools/sync_baseline.py --repo repo/hxwz4-release --canvas-w 960 --canvas-h 576
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ap = argparse.ArgumentParser()
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ap.add_argument("--repo", default=os.path.join(root, "repo", "hxwz4-release"))
ap.add_argument("--dest", default=os.path.join(root, "app", "src", "main", "assets", "www"))
ap.add_argument("--canvas-w", type=int, default=960)
ap.add_argument("--canvas-h", type=int, default=576)
a = ap.parse_args()

repo, dest, W, H = os.path.abspath(a.repo), os.path.abspath(a.dest), a.canvas_w, a.canvas_h

if not os.path.isdir(repo):
    sys.exit(f"Repo dir not found: {repo}\nClone it first: git clone --depth=1 https://cnb.cool/hxwz4/hxwz4-release.git {repo}")

if os.path.exists(dest):
    shutil.rmtree(dest)
os.makedirs(dest)

# copy everything except .git
for name in os.listdir(repo):
    if name == ".git":
        continue
    s, d = os.path.join(repo, name), os.path.join(dest, name)
    if os.path.isdir(s):
        shutil.copytree(s, d, ignore=shutil.ignore_patterns(".git"))
    else:
        shutil.copy2(s, d)

# mobile adaptation of the bundled index.html only
if W > 0 and H > 0:
    p = os.path.join(dest, "index.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8-sig") as f:
            html = f.read()

        html = re.sub(
            r'(lime\.embed\s*\(\s*"HxwzHaxe"\s*,\s*"content"\s*,\s*)1920(\s*,\s*)1152(\s*\)\s*;)',
            lambda m: f"{m.group(1)}{W}{m.group(2)}{H}, {{ allowHighDPI: true }}{m.group(3)}",
            html,
        )
        style = f"#content {{ background: #000000; width: {W}px; height: {H}px; transform-origin: 0 0; }}"
        html = re.sub(r"#content\s*\{[^}]*\}", lambda m: style, html)
        if not re.search(r"html,body[^}]*background", html):
            html = re.sub(
                r"html,body\s*\{[^}]*\}",
                lambda m: "html,body { margin: 0; padding: 0; height: 100%; overflow: hidden; background: #000; }",
                html,
            )
        if "移动端缩放" not in html:
            fit = f"""<script type="text/javascript">
\t// 移动端缩放 - 等比缩放 #content 容器并居中（兼容任意屏幕）
\t(function() {{
\t\tvar GW = {W}, GH = {H};
\t\tvar ct = document.getElementById('content');
\t\tfunction scale() {{
\t\t\tvar ww = window.innerWidth, wh = window.innerHeight;
\t\t\tvar s = Math.min(ww / GW, wh / GH);
\t\t\tct.style.transform = 'scale(' + s + ')';
\t\t\tct.style.marginLeft = ((ww - GW * s) / 2) + 'px';
\t\t\tct.style.marginTop  = ((wh - GH * s) / 2) + 'px';
\t\t}}
\t\tscale();
\t\twindow.addEventListener('resize', scale);
\t}})();
</script>
"""
            if "</body>" in html:
                html = html.replace("</body>", fit + "\n</body>")
            else:
                html += fit
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        print(f"Adapted bundled index.html: embed {W}x{H} + allowHighDPI + fit-to-screen")

# md5s.json (index.html and the manifest itself excluded; no BOM; "/" separators)
manifest = {}
for dp, dn, fn in os.walk(dest):
    dn[:] = [d for d in dn if d != ".git"]
    for n in fn:
        full = os.path.join(dp, n)
        rel = os.path.relpath(full, dest).replace(os.sep, "/")
        if rel in ("md5s.json", "index.html"):
            continue
        h = hashlib.md5()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        manifest[rel] = h.hexdigest()
manifest = dict(sorted(manifest.items()))
with open(os.path.join(dest, "md5s.json"), "w", encoding="utf-8", newline="") as f:
    json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))

total = sum(os.path.getsize(os.path.join(dp, n)) for dp, _, fn in os.walk(dest) for n in fn)
print(f"Baseline exported: {dest}")
print(f"Files: {len(manifest) + 1}, size: {total / 1048576:.1f} MB")
