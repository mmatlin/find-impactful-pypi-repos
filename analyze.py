import json
import re
import sqlite3
import time
import traceback
import sys

from itertools import islice
from pathlib import Path
from urllib.parse import urlparse

import requests

PYPI_PROJECT_ENDPOINT = "https://pypi.org/pypi/%s/json"
GH_REPO_ENDPOINT = "https://api.github.com/repos/%s"
PKGS_TO_ANALYZE = 1000
TOP_PYPI_PKGS_FILE = "top_pypi_pkgs.json"
OUT_FILE = f"analysis_{PKGS_TO_ANALYZE}.sqlite"
WAIT_TIME_BETWEEN_PKGS = 0.25 # seconds
PAT = open("GITHUB_PAT").read().trim()

# Data source (top 8000 pkgs monthly, ordered in decreasing download count):
# https://hugovk.github.io/top-pypi-packages/
# https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json
with open(TOP_PYPI_PKGS_FILE) as top_pypi_pkgs:
    pkgs = {
        # Dict order is maintained with Python 3.7+
        row["project"]: {"downloads": row["download_count"]}
        for row
        in json.load(top_pypi_pkgs)["rows"]
    }

to_del = list()
pkgs_done = 0
for pkg in pkgs:
    print(flush=True)
    time.sleep(WAIT_TIME_BETWEEN_PKGS)
    print(pkgs_done + 1)
    pypi_r = requests.get(PYPI_PROJECT_ENDPOINT % pkg)
    home_page = pypi_r.json()["info"]["home_page"]
    if home_page is None: # beautifulsoup4's home_page is JSON null :(
        home_page = ""
    u = urlparse(home_page)
    if u.netloc.removeprefix("www.") == "github.com":
        # Allowed repo name characters: https://stackoverflow.com/a/59082561
        match = re.fullmatch(r"/(.*?)/([A-Za-z0-9_.-]+)(?:/.*)?", u.path)
        if match is not None:
            owner_and_repo = f"{match.group(1)}/{match.group(2).removesuffix('.git')}"
            try:
                gh_r = requests.get(
                    GH_REPO_ENDPOINT % owner_and_repo,
                    headers={"Authorization": f"Bearer {PAT}"}
                    )
                if gh_r.status_code == 404:
                    print(f"Home page for package \"{pkg}\" ({home_page}) is not a real GitHub repo (404), set to remove from analysis....")
                    to_del.append(pkg)
                    continue
                stars = gh_r.json()["stargazers_count"]
                dl_to_s_ratio = float(pkgs[pkg]["downloads"]) / stars
                pkgs[pkg]["stars"] = stars
                pkgs[pkg]["dl_to_s_ratio"] = dl_to_s_ratio
                print(pkg, stars, dl_to_s_ratio)
                pkgs_done += 1
                if pkgs_done == PKGS_TO_ANALYZE:
                    break
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                print(pkg)
                print()
                print(pypi_r.content)
                print()
                print(gh_r.content)
                to_del.append(pkg)
    else:
        print(f"Home page for package \"{pkg}\" ({home_page}) is not a GitHub URL, set to remove from analysis....")
        to_del.append(pkg)

for pkg in to_del:
    del pkgs[pkg]

Path(OUT_FILE).unlink(missing_ok=True)
con = sqlite3.connect(OUT_FILE)
con.execute("CREATE TABLE package(name, downloads, stars, dl_to_s_ratio)")
rows = sorted(
    [v | {"name": k} for k, v in islice(pkgs.items(), PKGS_TO_ANALYZE)],
    key=lambda row: -row["dl_to_s_ratio"]
)
con.executemany(
    "INSERT INTO package(name, downloads, stars, dl_to_s_ratio) VALUES (:name, :downloads, :stars, :dl_to_s_ratio)",
    rows
    )
con.commit()
con.close()
