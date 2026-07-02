"""
UK Job Alert Bot
=================
Searches for jobs in the UK matching your target fields (inbound sales, PR,
marketing, advertising, and well-paying entry-level roles in any field) and
emails you when new listings appear.

This version reads its secrets (API keys, email login) from environment
variables, so it works with GitHub Actions (see SETUP_GITHUB_ACTIONS.md)
without you ever typing a password into the code itself. If an environment
variable isn't set, it falls back to the placeholder values below -- so it
also still works if you just want to run it locally on your own computer.
------------------------------------------------------------------
"""

import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from datetime import datetime

# ============================================================
# CONFIG — fill these in
# ============================================================

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "YOUR_ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "YOUR_ADZUNA_APP_KEY")

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "youraccount@gmail.com")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "your16charapppassword")
EMAIL_TO = os.environ.get("EMAIL_TO", "youraccount@gmail.com")

# Search terms — feel free to edit/add to these
SEARCH_TERMS = [
    "inbound sales",
    "public relations",
    "PR executive",
    "PR account executive",
    "marketing executive",
    "marketing coordinator",
    "advertising executive",
    "communications executive",
    "graduate marketing",
    "graduate communications",
    "entry level marketing",
]

# Minimum salary filter for "entry level, any field" searches (in GBP/year).
# Set to 0 if you don't want a salary floor.
MIN_SALARY = 26000

# How many results to fetch per search term, per run
RESULTS_PER_SEARCH = 20

SEEN_JOBS_FILE = "seen_jobs.json"

# ============================================================
# CODE — you shouldn't need to edit below this line
# ============================================================


def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f)


def search_adzuna(query, min_salary=0):
    """Search UK jobs via the Adzuna API for a given query string."""
    url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": RESULTS_PER_SEARCH,
        "content-type": "application/json",
    }
    if min_salary:
        params["salary_min"] = min_salary

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print(f"  [!] Search failed for '{query}': {e}")
        return []


def format_job(job):
    title = job.get("title", "Unknown title")
    company = job.get("company", {}).get("display_name", "Unknown company")
    location = job.get("location", {}).get("display_name", "Unknown location")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    url = job.get("redirect_url", "")

    salary_str = ""
    if salary_min and salary_max:
        salary_str = f"£{int(salary_min):,} - £{int(salary_max):,}"
    elif salary_min:
        salary_str = f"£{int(salary_min):,}+"

    lines = [f"• {title} — {company}", f"  {location}"]
    if salary_str:
        lines.append(f"  {salary_str}")
    lines.append(f"  {url}")
    return "\n".join(lines)


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    print(f"[{datetime.now()}] Running UK job search...")
    seen_jobs = load_seen_jobs()
    new_jobs = []

    for term in SEARCH_TERMS:
        # Only apply the salary floor to the generic "entry level" style searches
        apply_salary_filter = "entry level" in term or "graduate" in term
        min_salary = MIN_SALARY if apply_salary_filter else 0

        print(f"  Searching: {term}")
        results = search_adzuna(term, min_salary)

        for job in results:
            job_id = job.get("id")
            if job_id and job_id not in seen_jobs:
                seen_jobs.add(job_id)
                new_jobs.append(job)

    if new_jobs:
        print(f"  Found {len(new_jobs)} new job(s). Sending email...")
        body = f"Found {len(new_jobs)} new job listing(s):\n\n"
        body += "\n\n".join(format_job(job) for job in new_jobs)
        send_email(f"UK Job Alert: {len(new_jobs)} new listing(s)", body)
        save_seen_jobs(seen_jobs)
    else:
        print("  No new jobs found this run.")


if __name__ == "__main__":
    main()
