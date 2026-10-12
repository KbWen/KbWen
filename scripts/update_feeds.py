"""Fill the two auto-updated sections of README.md.

- recent_releases: the 5 newest GitHub releases across KbWen's public, non-fork, non-archived repos.
- recent_posts: the 5 newest posts (Chinese and English) from the blog RSS feed (www.kbwen.com/index.xml).

Standard library only. Uses GITHUB_TOKEN when present (Actions provides it); works without it at a lower rate limit.
Same inputs give the same README; if nothing changed, the file is left untouched.
"""
import email.utils
import json
import os
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

USER = "KbWen"
FEED = "https://www.kbwen.com/index.xml"
README = pathlib.Path(__file__).resolve().parent.parent / "README.md"
LIMIT = 5


def get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"{USER}-profile-readme"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def recent_releases():
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100"))
    items = []
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["private"]:
            continue
        for rel in json.loads(get(f"https://api.github.com/repos/{USER}/{repo['name']}/releases?per_page={LIMIT}")):
            if rel.get("draft") or rel.get("prerelease") or not rel.get("published_at"):
                continue
            items.append((rel["published_at"], repo["name"], rel["tag_name"], rel["html_url"]))
    items.sort(reverse=True)
    return [f"- [{name} {tag}]({url}) — {at[:10]}" for at, name, tag, url in items[:LIMIT]]


def recent_posts():
    root = ET.fromstring(get(FEED, accept="application/rss+xml, application/xml"))
    lines = []
    for item in root.iter("item"):
        title, link, date = item.findtext("title", ""), item.findtext("link", ""), item.findtext("pubDate", "")
        if not title or not link:
            continue
        day = email.utils.parsedate_to_datetime(date).strftime("%Y-%m-%d") if date else ""
        lines.append(f"- [{title}]({link}) — {day}")
        if len(lines) == LIMIT:
            break
    return lines


def replace(text, marker, lines):
    pattern = re.compile(rf"(<!-- {marker} starts -->\n).*?(<!-- {marker} ends -->)", re.S)
    body = "\n".join(lines) + "\n" if lines else ""
    new, n = pattern.subn(lambda m: m.group(1) + body + m.group(2), text)
    if n != 1:
        raise SystemExit(f"marker {marker} not found exactly once")
    return new


def main():
    text = README.read_text(encoding="utf-8")
    new = replace(text, "recent_releases", recent_releases())
    new = replace(new, "recent_posts", recent_posts())
    if new != text:
        with README.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
