#!/usr/bin/env python3
"""
Setup script for LinkedIn JobSpy - A LinkedIn Job Scraper Package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="linkedin-jobspy",
    version="1.0.0",
    description="A Python package for scraping job listings from LinkedIn",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Abhilash RS",
    author_email="your.email@example.com",
    url="https://github.com/A6h9lash/linkedin-jobspy",
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
        "Topic :: Scientific/Engineering :: Information Analysis",
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
            "pytest>=7.0.0",
            "pytest-cov",
        ],
    },
    keywords=[
        "linkedin",
        "jobs-scraper",
        "web-scraping",
        "job-search",
        "data-analysis",
        "career",
        "recruitment"
    ],
    project_urls={
        "Bug Reports": "https://github.com/A6h9lash/linkedin-jobspy/issues",
        "Source": "https://github.com/A6h9lash/linkedin-jobspy",
        "Documentation": "https://github.com/A6h9lash/linkedin-jobspy#readme",
    },
)
