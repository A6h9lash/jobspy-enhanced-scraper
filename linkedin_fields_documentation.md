# LinkedIn Job Scraping - All Available Fields

This document lists all the fields that are being captured and exported to CSV when scraping LinkedIn jobs.

## Core Job Information
- **id**: Unique identifier for the job (format: li-{job_id})
- **title**: Job title/position name
- **job_url**: Direct URL to the LinkedIn job posting
- **job_url_direct**: Direct application URL (if available)
- **description**: Full job description (when linkedin_fetch_description=True)
- **date_posted**: Date when the job was posted (now properly populated with the fix)
- **is_remote**: Boolean indicating if the job is remote
- **listing_type**: Type of job listing

## Company Information
- **company_name**: Name of the hiring company
- **company_url**: Company's LinkedIn profile URL
- **company_url_direct**: Company's direct website URL
- **company_industry**: Industry/sector of the company
- **company_addresses**: Company addresses (if available)
- **company_num_employees**: Number of employees at the company
- **company_revenue**: Company revenue information
- **company_description**: Company description
- **company_logo**: URL to company logo
- **company_rating**: Company rating (if available)
- **company_reviews_count**: Number of company reviews

## Location Information
- **location_city**: City where the job is located
- **location_state**: State/province where the job is located
- **location_country**: Country where the job is located
- **location_display**: Formatted location string (e.g., "San Francisco, CA, USA")

## Employment Details
- **job_type**: Type of employment (Full-time, Part-time, Contract, etc.)
- **job_level**: Seniority level (Entry, Mid, Senior, etc.)
- **job_function**: Job function/category
- **experience_range**: Required experience range
- **vacancy_count**: Number of open positions

## Compensation Information
- **compensation_min**: Minimum salary amount
- **compensation_max**: Maximum salary amount
- **compensation_currency**: Currency code (USD, EUR, etc.)
- **compensation_interval**: Pay period (yearly, monthly, hourly, etc.)

## Additional Information
- **emails**: Email addresses found in job description
- **skills**: Required skills (if available)
- **work_from_home_type**: Work arrangement type (Remote, Hybrid, On-site)
- **banner_photo_url**: Job posting banner image URL

## Notes
- Some fields may be `None` or empty depending on the job posting and LinkedIn's data availability
- The `date_posted` field has been fixed to properly populate with actual dates instead of remaining `None`
- Location fields are extracted from the job posting and may vary in completeness
- Compensation information is only available when explicitly listed in the job posting
- Full job descriptions are only fetched when `linkedin_fetch_description=True` is set

## CSV Export
All these fields are exported to a CSV file with the filename format: `linkedin_jobs_YYYYMMDD_HHMMSS.csv`
