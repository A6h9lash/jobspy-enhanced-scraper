"""
Basic tests for LinkedIn JobSpy package
"""

import pytest
from linkedin_jobspy import LinkedIn, ScraperInput, Site, Country, JobType


def test_import():
    """Test that all main classes can be imported"""
    assert LinkedIn is not None
    assert ScraperInput is not None
    assert Site is not None
    assert Country is not None
    assert JobType is not None


def test_linkedin_initialization():
    """Test LinkedIn scraper initialization"""
    scraper = LinkedIn()
    assert scraper is not None
    assert scraper.base_url == "https://www.linkedin.com"


def test_scraper_input_creation():
    """Test ScraperInput model creation"""
    scraper_input = ScraperInput(
        site_type=[Site.LINKEDIN],
        search_term="Data Scientist",
        location="San Francisco, CA",
        country=Country.USA,
        results_wanted=10
    )
    
    assert scraper_input.search_term == "Data Scientist"
    assert scraper_input.location == "San Francisco, CA"
    assert scraper_input.country == Country.USA
    assert scraper_input.results_wanted == 10


if __name__ == "__main__":
    pytest.main([__file__])
