#!/usr/bin/env python3
"""
Test script for LinkedIn Data Analyst job scraping
Pulls Data Analyst jobs posted in the United States in the past 24 hours
"""

import sys
import os
from datetime import datetime

# Add the jobspy_enhanced module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'jobspy_enhanced'))

from jobspy_enhanced.linkedin import LinkedIn
from jobspy_enhanced.model import ScraperInput, Site, Country, JobType, DescriptionFormat


def test_linkedin_data_analyst():
    """
    Test function to scrape Data Analyst jobs from LinkedIn
    """
    print("=" * 60)
    print("LinkedIn Data Analyst Jobs Test")
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
        results_wanted=500,  # Get 20 results
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
            print("Job Results:")
            print("-" * 40)
            
            for i, job in enumerate(job_response.jobs, 1):
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
        else:
            print("No jobs found matching the criteria.")
            
    except Exception as e:
        print(f"Error occurred during scraping: {str(e)}")
        return False
    
    print("=" * 60)
    print("LinkedIn test completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_linkedin_data_analyst()
    sys.exit(0 if success else 1)
