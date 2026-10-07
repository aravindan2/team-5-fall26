# Team Project repo

[![Checks](https://github.com/gcivil-nyu-org/team-5-fall26/actions/workflows/checks.yml/badge.svg?event=pull_request)](https://github.com/gcivil-nyu-org/team-5-fall26/actions/workflows/checks.yml?query=event%3Apull_request)

## Local development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

The sign-up page is at http://127.0.0.1:8000/accounts/register/ and the login
page is at http://127.0.0.1:8000/accounts/login/.

In development, emails such as password reset links aren't actually sent;
they're printed in the terminal running `runserver`.

## NYC Parks events

The landing page lists upcoming NYC Parks events imported from the city's
[open data feed](https://data.cityofnewyork.us/api/v3/views/w3wp-dpdi).
Sync the database from the feed with:

```bash
python manage.py sync_events
```

The command fetches every record, creates new events, updates events whose
content changed, leaves unchanged events untouched, and marks events done
once their end time has passed. The feed only publishes a rolling two-week
window, but events stay in the database after they disappear from it.

Run it once to seed your local database, then schedule it hourly with cron
(use absolute paths, because cron runs with a minimal environment):

```cron
0 * * * * cd /path/to/team-5-fall26 && /path/to/.venv/bin/python manage.py sync_events >> /var/log/team5_sync.log 2>&1
```

## Checks

The badge above shows the combined status of the Black, Flake8, and coverage jobs
in the pull request workflow. Click it to see workflow runs and individual job
results.

Run these before opening a pull request:

```bash
black --check .
flake8
coverage run manage.py test
coverage report  # fails below 95% coverage
```
