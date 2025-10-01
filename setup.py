#!/usr/bin/env python3
"""
Setup script for JobSpy Enhanced Scraper
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="jobspy-enhanced-scraper",
    version="1.0.0",
    description="Enhanced job scraper for LinkedIn, Indeed, Glassdoor, ZipRecruiter with improved filtering capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/A6h9lash/jobspy-enhanced-scraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "pandas>=2.1.0",
        "numpy>=1.26.3",
        "pydantic>=2.3.0",
        "tls-client>=1.0.1",
        "markdownify>=1.1.0",
        "regex>=2024.4.28",
    ],
    extras_require={
        "dev": [
            "jupyter>=1.0.0",
            "black",
            "pre-commit",
        ],
    },
    keywords=[
        "jobs-scraper",
        "linkedin",
        "indeed", 
        "glassdoor",
        "ziprecruiter",
        "naukri",
        "enhanced",
        "filtering",
        "web-scraping",
        "job-search",
        "data-analysis"
    ],
    project_urls={
        "Bug Reports": "https://github.com/A6h9lash/jobspy-enhanced-scraper/issues",
        "Source": "https://github.com/A6h9lash/jobspy-enhanced-scraper",
        "Documentation": "https://github.com/A6h9lash/jobspy-enhanced-scraper#readme",
    },
)
