# Live job postings

`.github/workflows/jobs-live.yml` runs `fetch_jobs.py` every day at 6:17 AM Toronto time (and on demand from the Actions tab).
It reads postings from the sources in `jobs_sources.json`, keeps only occupational health and safety (OHS) and construction
management (CM) roles in Canada (`jobs_filter.py`), drops postings older than 30 days and duplicates, caps the list at 150,
checks the result (`check_jobs.py`) and commits `jobs-live.json`, then its `deploy` job publishes the site to GitHub Pages.
The page reads that file; nothing else is fetched by visitors.

Pages is set to build from GitHub Actions: `.github/workflows/pages.yml` deploys every push to `main`. The daily refresh deploys
from its own workflow because a push made with `GITHUB_TOKEN` does not start other workflows.

Sources are official APIs or feeds published for sharing. Each entry in `jobs_sources.json` records the terms that were checked;
sources whose terms do not allow reuse are listed with `"enabled": false`.

Keys (optional; a source is skipped when its key is missing). Add them in Settings > Secrets and variables > Actions:

| Secret | Where to get it |
| --- | --- |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Free developer account at https://developer.adzuna.com/ . Adzuna also requires the "Jobs by Adzuna" label with its official logo on each posting: save the logo from Adzuna's press page as `assets/adzuna-logo.png`, or Adzuna stays off. |
| `JOOBLE_API_KEY` | Request form at https://jooble.org/api/about (key sent by email after review). |

`blocklist_sha256.json` holds hashed words and names the site must never show; matching postings are dropped.
Run locally: `python scripts/fetch_jobs.py --out jobs-live.json` (Python 3.9+, standard library only).
