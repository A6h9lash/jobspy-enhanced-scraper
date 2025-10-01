#!/usr/bin/env python3
"""
Test script for LinkedIn Data Analyst job scraping with CSV export
Pulls Data Analyst jobs posted in the United States and exports to CSV
"""

import sys
import os
import csv
from datetime import datetime

# Add the jobspy_enhanced module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'jobspy_enhanced'))

from jobspy_enhanced.linkedin import LinkedIn
from jobspy_enhanced.model import ScraperInput, Site, Country, JobType, DescriptionFormat


def export_jobs_to_csv(jobs, filename=None):
    """
    Export job data to CSV file with all available fields
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_jobs_{timestamp}.csv"
    
    # Define all possible fields from JobPost model
    fieldnames = [
        'id',
        'title', 
        'company_name',
        'job_url',
        'job_url_direct',
        'location_city',
        'location_state', 
        'location_country',
        'location_display',
        'description',
        'company_url',
        'company_url_direct',
        'job_type',
        'compensation_min',
        'compensation_max',
        'compensation_currency',
        'compensation_interval',
        'date_posted',
        'emails',
        'is_remote',
        'listing_type',
        'job_level',
        'company_industry',
        'company_addresses',
        'company_num_employees',
        'company_revenue',
        'company_description',
        'company_logo',
        'banner_photo_url',
        'job_function',
        'skills',
        'experience_range',
        'company_rating',
        'company_reviews_count',
        'vacancy_count',
        'work_from_home_type'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for job in jobs:
            row = {
                'id': job.id,
                'title': job.title,
                'company_name': job.company_name,
                'job_url': job.job_url,
                'job_url_direct': job.job_url_direct,
                'location_city': job.location.city if job.location else None,
                'location_state': job.location.state if job.location else None,
                'location_country': job.location.country.value[0] if job.location and job.location.country else None,
                'location_display': job.location.display_location() if job.location else None,
                'description': job.description,
                'company_url': job.company_url,
                'company_url_direct': job.company_url_direct,
                'job_type': ', '.join([jt.value[0] for jt in job.job_type]) if job.job_type else None,
                'compensation_min': job.compensation.min_amount if job.compensation else None,
                'compensation_max': job.compensation.max_amount if job.compensation else None,
                'compensation_currency': job.compensation.currency if job.compensation else None,
                'compensation_interval': job.compensation.interval.value if job.compensation and job.compensation.interval else None,
                'date_posted': job.date_posted.isoformat() if job.date_posted else None,
                'emails': ', '.join(job.emails) if job.emails else None,
                'is_remote': job.is_remote,
                'listing_type': job.listing_type,
                'job_level': job.job_level,
                'company_industry': job.company_industry,
                'company_addresses': job.company_addresses,
                'company_num_employees': job.company_num_employees,
                'company_revenue': job.company_revenue,
                'company_description': job.company_description,
                'company_logo': job.company_logo,
                'banner_photo_url': job.banner_photo_url,
                'job_function': job.job_function,
                'skills': ', '.join(job.skills) if job.skills else None,
                'experience_range': job.experience_range,
                'company_rating': job.company_rating,
                'company_reviews_count': job.company_reviews_count,
                'vacancy_count': job.vacancy_count,
                'work_from_home_type': job.work_from_home_type
            }
            writer.writerow(row)
    
    return filename


def test_linkedin_data_analyst_with_csv():
    """
    Test function to scrape Data Analyst jobs from LinkedIn and export to CSV
    """
    print("=" * 60)
    print("LinkedIn Data Analyst Jobs Test with CSV Export")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize LinkedIn scraper
    scraper = LinkedIn()
    
    # Configure search parameters
    scraper_input = ScraperInput(
        site_type=[Site.LINKEDIN],
        search_term="Data Analyst",
        country=Country.USA,
        results_wanted=500,  # Get 50 results for CSV export
        hours_old=24,  # Jobs posted in the past 24 hours
        job_type=JobType.FULL_TIME,
        description_format=DescriptionFormat.MARKDOWN,
        linkedin_fetch_description=True  # Fetch full job descriptions
    )
    
    print("Search Parameters:")
    print(f"  Search Term: {scraper_input.search_term}")
    print(f"  Location: {scraper_input.location}")
    print(f"  Country: {scraper_input.country.value[0]}")
    print(f"  Results Wanted: {scraper_input.results_wanted}")
    print(f"  Hours Old: {scraper_input.hours_old}")
    print(f"  Job Type: {scraper_input.job_type.value[0] if scraper_input.job_type else 'Any'}")
    print()
    
    try:
        # Perform the search
        print("Starting LinkedIn job search...")
        job_response = scraper.scrape(scraper_input)
        
        print(f"Search completed!")
        print(f"Total jobs found: {len(job_response.jobs)}")
        print()
        
        if job_response.jobs:
            # Export to CSV
            csv_filename = export_jobs_to_csv(job_response.jobs)
            print(f"Jobs exported to CSV: {csv_filename}")
            print()
            
            # Display summary of first few jobs
            print("Job Results Summary (first 5 jobs):")
            print("-" * 40)
            
            for i, job in enumerate(job_response.jobs[:5], 1):
                print(f"{i}. {job.title}")
                print(f"   Company: {job.company_name}")
                print(f"   Location: {job.location.display_location() if job.location else 'N/A'}")
                print(f"   Remote: {'Yes' if job.is_remote else 'No'}")
                print(f"   Posted: {job.date_posted}")
                print(f"   URL: {job.job_url}")
                
                if job.compensation:
                    comp = job.compensation
                    if comp.min_amount and comp.max_amount:
                        print(f"   Salary: ${comp.min_amount:,.0f} - ${comp.max_amount:,.0f} {comp.currency}")
                    elif comp.min_amount:
                        print(f"   Salary: ${comp.min_amount:,.0f}+ {comp.currency}")
                
                if job.job_type:
                    job_types = [jt.value[0] for jt in job.job_type]
                    print(f"   Job Type: {', '.join(job_types)}")
                
                if job.company_industry:
                    print(f"   Industry: {job.company_industry}")
                
                if job.job_level:
                    print(f"   Level: {job.job_level}")
                
                print()
            
            if len(job_response.jobs) > 5:
                print(f"... and {len(job_response.jobs) - 5} more jobs in CSV file")
                print()
        else:
            print("No jobs found matching the criteria.")
            
    except Exception as e:
        print(f"Error occurred during scraping: {str(e)}")
        return False
    
    print("=" * 60)
    print("LinkedIn test with CSV export completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_linkedin_data_analyst_with_csv()
    sys.exit(0 if success else 1)
