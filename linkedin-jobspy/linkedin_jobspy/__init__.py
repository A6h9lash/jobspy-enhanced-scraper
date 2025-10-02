"""
LinkedIn JobSpy - LinkedIn Job Scraper Package

A standalone Python package for scraping job listings from LinkedIn.
"""

__version__ = "1.0.0"
__author__ = "Abhilash RS"
__email__ = "your.email@example.com"

from .scraper import LinkedIn
from .models import JobPost, JobResponse, JobType, Location, Country, Compensation, ScraperInput, Site
from .exceptions import LinkedInException

__all__ = [
    "LinkedIn",
    "JobPost", 
    "JobResponse",
    "JobType",
    "Location", 
    "Country",
    "Compensation",
    "ScraperInput",
    "Site",
    "LinkedInException"
]
