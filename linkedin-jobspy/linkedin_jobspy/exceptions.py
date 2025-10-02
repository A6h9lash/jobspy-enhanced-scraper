"""
LinkedIn JobSpy Exceptions

Custom exceptions for LinkedIn job scraping operations.
"""


class LinkedInException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with LinkedIn")
