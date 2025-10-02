# LinkedIn JobSpy

A Python package for scraping job listings from LinkedIn.

## Installation

```bash
pip install linkedin-jobspy
```

## Quick Start

```python
from linkedin_jobspy import LinkedIn, ScraperInput, Site, Country, JobType

# Initialize the scraper
scraper = LinkedIn()

# Create search parameters
search_params = ScraperInput(
    site_type=[Site.LINKEDIN],
    search_term="Data Scientist",
    location="San Francisco, CA",
    country=Country.USA,
    results_wanted=50,
    job_type=JobType.FULL_TIME,
    is_remote=True
)

# Scrape jobs
jobs = scraper.scrape(search_params)

# Process results
for job in jobs.jobs:
    print(f"{job.title} at {job.company_name}")
    print(f"Location: {job.location.display_location()}")
    print(f"URL: {job.job_url}")
    print("-" * 50)
```

## Features

- Search LinkedIn job listings by keywords and location
- Filter by job type, remote work, company, and more
- Extract detailed job information including descriptions
- Support for proxy usage and rate limiting
- Export results to various formats

## Search Parameters

- `search_term`: Job title or keywords
- `location`: City, state, or "Remote"
- `country`: Country enum (e.g., Country.USA)
- `job_type`: JobType enum (FULL_TIME, PART_TIME, CONTRACT, etc.)
- `is_remote`: Boolean for remote jobs
- `easy_apply`: Boolean for LinkedIn Easy Apply jobs
- `results_wanted`: Number of jobs to retrieve
- `hours_old`: Filter by posting time (in hours)
- `linkedin_company_ids`: List of specific company IDs
- `linkedin_fetch_description`: Boolean to fetch full descriptions

## Job Data

Each job includes:
- Basic info: title, company, location, URL
- Details: description, job type, level, industry
- Compensation: salary range and currency (if available)
- Metadata: posting date, remote status, emails

## Requirements

- Python 3.10+
- Core dependencies: requests, beautifulsoup4, pandas, pydantic

## License

MIT License - see LICENSE file for details.

## Disclaimer

For educational and research purposes only. Please comply with LinkedIn's Terms of Service.
