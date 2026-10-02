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
