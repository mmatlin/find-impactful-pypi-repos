# find-impactful-pypi-repos
This quick-and-dirty script finds the Python packages on GitHub that have the most downloads for the least stars (one interpretation: most impact for being least known).

To prep for analysis, just run `./download_data.sh` and place a GitHub PAT in a file named `GITHUB_PAT` (this is to have access to GitHub's API rate limit for authenticated users).

You can also just run `./download_data.sh` to get the most recent data on the 8000 most downloaded PyPI packages.

To run the analysis, just run `analyze.py`, that's all.
