"""Fetch GitHub stats into assets/data/stats.json (stdlib only).

Totals include private repos and commits, so the token needs `repo` scope:
  - locally: `gh auth token` is used automatically
  - in Actions: add a fine-grained/classic PAT as the PROFILE_TOKEN secret
If only the default GITHUB_TOKEN is available, private totals can't be seen, so the
previous values are kept instead of being overwritten with smaller public-only numbers.
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "profile.config.json").read_text())
OUT = ROOT / "assets" / "data" / "stats.json"
LOGIN = CONFIG["login"]


def token():
    for var in ("PROFILE_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var], var == "PROFILE_TOKEN"
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip(), True
    except Exception:
        sys.exit("No PROFILE_TOKEN/GITHUB_TOKEN and `gh auth token` failed")


TOKEN, FULL = token()


def call(url, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search_count(kind, q):
    return call(f"https://api.github.com/search/{kind}?per_page=1&q={urllib.parse.quote(q, safe=':>=+')}")["total_count"]


QUERY = """
query($login: String!) {
  user(login: $login) {
    all: repositories(ownerAffiliations: OWNER) { totalCount }
    public: repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { name stargazerCount }
    }
  }
}
"""


def main():
    year = datetime.now(timezone.utc).year
    data = call("https://api.github.com/graphql", {"query": QUERY, "variables": {"login": LOGIN}})
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    u = data["data"]["user"]
    pub = u["public"]["nodes"]
    stats = {
        "repos": u["all"]["totalCount"],
        "public_repos": u["public"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in pub),
        "stars_by_repo": {r["name"]: r["stargazerCount"] for r in pub if r["stargazerCount"]},
        "year": year,
        "commits_year": search_count("commits", f"author:{LOGIN} author-date:>={year}-01-01"),
        "prs_year": search_count("issues", f"author:{LOGIN} is:pr created:>={year}-01-01"),
        "commits_total": search_count("commits", f"author:{LOGIN}"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if not FULL and OUT.exists():
        old = json.loads(OUT.read_text())
        for k in ("repos", "commits_year", "prs_year", "commits_total"):
            if old.get(k, 0) > stats[k] and not (k.endswith("_year") and old.get("year") != year):
                stats[k] = old[k]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"stats: {stats['repos']} repos, {stats['commits_year']} commits + {stats['prs_year']} PRs in {year}, "
          f"{stats['stars']} stars ({'full' if FULL else 'public-only token'})")


if __name__ == "__main__":
    main()
