"""
LinkedIn specific utility functions for job scraping.
"""

from bs4 import BeautifulSoup

from .models import JobType, Location
from .utils import get_enum_from_job_type


def job_type_code(job_type_enum: JobType) -> str:
    return {
        JobType.FULL_TIME: "F",
        JobType.PART_TIME: "P",
        JobType.INTERNSHIP: "I",
        JobType.CONTRACT: "C",
        JobType.TEMPORARY: "T",
    }.get(job_type_enum, "")


def parse_job_type(soup_job_type: BeautifulSoup) -> list[JobType] | None:
    """
    Gets the job type from job page
    :param soup_job_type:
    :return: formatted job type
    """
    h3_tag = soup_job_type.find(
        "h3",
        {
            "class": "description__job-criteria-subheader",
            "string": lambda text: text and "Employment type" in text,
        },
    )
    employment_type = None
    if h3_tag:
        employment_type_span = h3_tag.find_next_sibling("span")
        if employment_type_span:
            employment_type = employment_type_span.get_text(strip=True)

    if employment_type:
        employment_type = employment_type.lower().replace("-", "")
        employment_type = employment_type.replace(" ", "")

        job_type_enum = get_enum_from_job_type(employment_type)
        if job_type_enum:
            return [job_type_enum]

    return None


def parse_job_level(
    soup_job_level: BeautifulSoup,
) -> str | None:
    """
    Gets the job level from job page
    :param soup_job_level:
    :return: formatted job level
    """
    h3_tag = soup_job_level.find(
        "h3",
        {
            "class": "description__job-criteria-subheader",
            "string": lambda text: text and "Seniority level" in text,
        },
    )

    job_level = None
    if h3_tag:
        job_level_span = h3_tag.find_next_sibling("span")
        if job_level_span:
            job_level = job_level_span.get_text().strip()

    return job_level


def parse_company_industry(
    soup_company_industry: BeautifulSoup,
) -> str | None:
    """
    Gets the company industry from job page
    :param soup_company_industry:
    :return: formatted company industry
    """
    h3_tag = soup_company_industry.find(
        "h3",
        {
            "class": "description__job-criteria-subheader",
            "string": lambda text: text and "Industries" in text,
        },
    )

    company_industry = None
    if h3_tag:
        company_industry_span = h3_tag.find_next_sibling("span")
        if company_industry_span:
            company_industry = company_industry_span.get_text().strip()

    return company_industry


def is_job_remote(job_detail: BeautifulSoup) -> bool:
    """
    Check if the job is remote by examining the job details
    """
    if not job_detail:
        return False
    
    # Check in job criteria section
    criteria_spans = job_detail.find_all("span", class_="description__job-criteria-text")
    for span in criteria_spans:
        text = span.get_text(strip=True).lower()
        if any(keyword in text for keyword in ["remote", "work from home", "telecommute"]):
            return True
    
    # Check in the description text
    description_text = job_detail.get_text().lower()
    remote_keywords = ["remote", "work from home", "telecommute", "distributed team"]
    
    return any(keyword in description_text for keyword in remote_keywords)
