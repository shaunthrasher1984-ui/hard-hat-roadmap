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



## Weekly listings refresh

`.github/workflows/weekly-refresh.yml` runs every Monday at 10:00 UTC (about 6:00 AM Atlantic Standard Time / 7:00 AM Atlantic Daylight Time in America/Moncton) and on demand from the Actions tab. It has no hour-of-day skip gate, so a late GitHub cron still runs.

It refreshes `jobs-live.json`, re-checks every link in `internships.json` (marks `closed` or `not_found` when the posting is gone; leaves the previous status when the check is inconclusive), writes `weekly-update.json` (last updated date plus new/closed counts), copies both JSON files into `index.html`, commits those data files, and deploys Pages. A commit is expected every week so GitHub does not auto-disable the scheduled workflow after 60 days of inactivity.

The daily `jobs-live.yml` workflow still exists. It no longer requires the runner clock to be 6 AM Toronto; it skips only if `jobs-live.json` was already generated today.

Run locally:

```
cp jobs-live.json /tmp/prev-jobs-live.json
cp internships.json /tmp/prev-internships.json
python3 scripts/fetch_jobs.py --out jobs-live.json
python3 scripts/check_jobs.py jobs-live.json
python3 scripts/check_internships.py internships.json
python3 scripts/sync_internships.py
python3 scripts/write_weekly_update.py --prev-jobs /tmp/prev-jobs-live.json --jobs jobs-live.json --prev-internships /tmp/prev-internships.json --internships internships.json --out weekly-update.json
```


## Soft-launch note
Python fetch/filter scripts are **not** shipped in this public preview build (proprietary pipeline). Keep them in a private source repo; CI should run them privately and commit only `jobs-live.json`.


## Paid internships & student roles

`internships.json` is a curated list (not the daily jobs-live refresh). Edit that file to add, update or close a posting, then run:

```
python3 scripts/sync_internships.py
```

to copy it into the `<script id="internships-data">` block in `index.html`. Fields: `employer`, `title`, `location`, `type`, `kind` (`student` or `full_time`), `link`, `status` (`live`, `closed`, or `not_found`), `pay` (only when the employer posting states it; otherwise leave blank), `note`, `checked` (YYYY-MM-DD). For a closed or missing posting, keep `link` pointed at the posting if it still exists, otherwise at the employer careers page.

## Daily Finds

`posts.json` at the repo root is the curated Daily Finds list (jobs, free training and volunteer opportunities).
The Daily Finds page reads that file; jobs older than 30 days, or with `"status": "closed"`, are hidden.
Training and volunteer items stay visible unless they have an `end_date` that has passed.

To add one find after a morning post, from the repo root:

```bash
python3 scripts/add-post.py \
  --id p-2026-11-26-short-slug \
  --date 2026-11-26 \
  --track OHS \
  --type job \
  --title "Role title (City)" \
  --org "Employer" \
  --summary "One sentence for a job seeker." \
  --url "https://example.com/job" \
  --status open

git add posts.json
git commit -m "Add Daily Find: Role title (City)"
git push origin main
```

`--track` is `OHS`, `CM` or `Both`. `--type` is `job`, `free_training` or `volunteer`.
Add `--end-date YYYY-MM-DD` when a free-training offer expires, and `--resource-id r123` when the same item already lives in `resources.json`.
Check the file without writing: `python3 scripts/add-post.py --validate-only`.
