from __future__ import annotations

import math
import random
import time
from datetime import datetime, date
from typing import Optional
from urllib.parse import urlparse, urlunparse, unquote

import regex as re
from bs4 import BeautifulSoup
from bs4.element import Tag

from jobspy_enhanced.exception import LinkedInException
from jobspy_enhanced.linkedin.constant import headers
from jobspy_enhanced.linkedin.util import (
    is_job_remote,
    job_type_code,
    parse_job_type,
    parse_job_level,
    parse_company_industry
)
from jobspy_enhanced.model import (
    JobPost,
    Location,
    JobResponse,
    Country,
    Compensation,
    DescriptionFormat,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy_enhanced.util import (
    extract_emails_from_text,
    currency_parser,
    markdown_converter,
    plain_converter,
    create_session,
    remove_attributes,
    create_logger,
)

log = create_logger("LinkedIn")


class LinkedIn(Scraper):
    base_url = "https://www.linkedin.com"
    delay = 3
    band_delay = 4
    jobs_per_page = 25

    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None, user_agent: str | None = None
    ):
        """
        Initializes LinkedInScraper with the LinkedIn job search url
        """
        super().__init__(Site.LINKEDIN, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=ca_cert,
            is_tls=False,
            has_retry=True,
            delay=5,
            clear_cookies=True,
        )
        self.session.headers.update(headers)
        self.scraper_input = None
        self.country = "worldwide"
        self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrapes LinkedIn for jobs with scraper_input criteria
        :param scraper_input:
        :return: job_response
        """
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        start = scraper_input.offset // 10 * 10 if scraper_input.offset else 0
        request_count = 0
        seconds_old = (
            scraper_input.hours_old * 3600 if scraper_input.hours_old else None
        )
        continue_search = (
            lambda: len(job_list) < scraper_input.results_wanted and start < 1000
        )
        while continue_search():
            request_count += 1
            log.info(
                f"search page: {request_count} / {math.ceil(scraper_input.results_wanted / 10)}"
            )
            print(f"📡 Fetching page {request_count}... (Found {len(job_list)} jobs so far)")
            params = {
                "keywords": scraper_input.search_term,
                "location": scraper_input.location,
                "distance": scraper_input.distance,
                "pageNum": 0,
                "start": start,
            }
            
            # Add all applicable filters (no longer mutually exclusive)
            if scraper_input.is_remote:
                params["f_WT"] = 2
                
            if scraper_input.job_type:
                params["f_JT"] = job_type_code(scraper_input.job_type)
                
            if scraper_input.easy_apply is not None:
                if scraper_input.easy_apply:
                    params["f_AL"] = "true"
                else:
                    params["f_AL"] = "false"
                
            if scraper_input.linkedin_company_ids:
                params["f_C"] = ",".join(map(str, scraper_input.linkedin_company_ids))
                
            # Add experience level filter if specified
            if scraper_input.experience_level is not None:
                params["f_E"] = scraper_input.experience_level
                
            # Add time filter if specified (can now be combined with other filters)
            if seconds_old is not None:
                params["f_TPR"] = f"r{seconds_old}"

            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = self.session.get(
                    f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?",
                    params=params,
                    timeout=10,
                )
                if response.status_code not in range(200, 400):
                    if response.status_code == 429:
                        err = (
                            f"429 Response - Blocked by LinkedIn for too many requests"
                        )
                    else:
                        err = f"LinkedIn response status code {response.status_code}"
                        err += f" - {response.text}"
                    log.error(err)
                    return JobResponse(jobs=job_list)
            except Exception as e:
                if "Proxy responded with" in str(e):
                    log.error(f"LinkedIn: Bad proxy")
                else:
                    log.error(f"LinkedIn: {str(e)}")
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="base-search-card")
            if len(job_cards) == 0:
                return JobResponse(jobs=job_list)

            for job_card in job_cards:
                href_tag = job_card.find("a", class_="base-card__full-link")
                if href_tag and "href" in href_tag.attrs:
                    href = href_tag.attrs["href"].split("?")[0]
                    job_id = href.split("-")[-1]

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    try:
                        fetch_desc = scraper_input.linkedin_fetch_description
                        job_post = self._process_job(job_card, job_id, fetch_desc)
                        if job_post:
                            job_list.append(job_post)
                            print(f"   ✅ Job {len(job_list)}: {job_post.title} at {job_post.company_name}")
                        else:
                            print(f"   ⏭️  Job filtered out (likely easy apply)")
                        if not continue_search():
                            break
                    except Exception as e:
                        print(f"   ❌ Error processing job {job_id}: {str(e)}")
                        raise LinkedInException(str(e))

            if continue_search():
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                start += len(job_cards)

        job_list = job_list[: scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_job(
        self, job_card: Tag, job_id: str, full_descr: bool
    ) -> Optional[JobPost]:
        # Note: Easy apply detection is now done at the job page level in _get_job_details
        # This ensures more accurate detection since the information is only available there
        salary_tag = job_card.find("span", class_="job-search-card__salary-info")

        compensation = description = None
        if salary_tag:
            salary_text = salary_tag.get_text(separator=" ").strip()
            salary_values = [currency_parser(value) for value in salary_text.split("-")]
            salary_min = salary_values[0]
            salary_max = salary_values[1]
            currency = salary_text[0] if salary_text[0] != "$" else "USD"

            compensation = Compensation(
                min_amount=int(salary_min),
                max_amount=int(salary_max),
                currency=currency,
            )

        title_tag = job_card.find("span", class_="sr-only")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        company_tag = job_card.find("h4", class_="base-search-card__subtitle")
        company_a_tag = company_tag.find("a") if company_tag else None
        company_url = (
            urlunparse(urlparse(company_a_tag.get("href"))._replace(query=""))
            if company_a_tag and company_a_tag.has_attr("href")
            else ""
        )
        company = company_a_tag.get_text(strip=True) if company_a_tag else "N/A"

        metadata_card = job_card.find("div", class_="base-search-card__metadata")
        location = self._get_location(metadata_card)

        # Try multiple selectors for date posted information
        date_posted = None
        
        if metadata_card:
            # Try different possible selectors for date information
            datetime_tag = None
            
            # First try: job-search-card__listdate class
            datetime_tag = metadata_card.find("time", class_="job-search-card__listdate")
            
            # Second try: any time tag with datetime attribute
            if not datetime_tag:
                datetime_tag = metadata_card.find("time", attrs={"datetime": True})
            
            # Third try: look for relative time text and parse it
            if not datetime_tag:
                time_elements = metadata_card.find_all("time")
                for time_elem in time_elements:
                    if time_elem.get("datetime"):
                        datetime_tag = time_elem
                        break
            
            # Fourth try: look for any element with datetime attribute
            if not datetime_tag:
                datetime_tag = metadata_card.find(attrs={"datetime": True})
            
            # Parse the datetime if found
            if datetime_tag and "datetime" in datetime_tag.attrs:
                datetime_str = datetime_tag["datetime"]
                try:
                    # Try different datetime formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"]:
                        try:
                            date_posted = datetime.strptime(datetime_str, fmt).date()
                            break
                        except ValueError:
                            continue
                except:
                    date_posted = None
            
            # If still no date found, try to parse relative time text
            if not date_posted:
                date_posted = self._parse_relative_date(metadata_card)
        job_details = {}
        if full_descr:
            print(f"   🔍 Fetching details for job {job_id}...")
            job_details = self._get_job_details(job_id)
            if job_details is None:
                # Job was filtered out (e.g., easy apply job when easy_apply=False)
                print(f"   ⏭️  Job {job_id} filtered out (easy apply)")
                return None
            description = job_details.get("description")
            print(f"   📄 Job details fetched successfully")
        is_remote = is_job_remote(title, description, location)

        return JobPost(
            id=f"li-{job_id}",
            title=title,
            company_name=company,
            company_url=company_url,
            location=location,
            is_remote=is_remote,
            date_posted=date_posted,
            job_url=f"{self.base_url}/jobs/view/{job_id}",
            compensation=compensation,
            job_type=job_details.get("job_type"),
            job_level=job_details.get("job_level", "").lower(),
            company_industry=job_details.get("company_industry"),
            description=job_details.get("description"),
            job_url_direct=job_details.get("job_url_direct"),
            emails=extract_emails_from_text(description),
            company_logo=job_details.get("company_logo"),
            job_function=job_details.get("job_function"),
        )

    def _get_job_details(self, job_id: str) -> dict:
        """
        Retrieves job description and other job details by going to the job page url
        :param job_page_url:
        :return: dict
        """
        # Try multiple times with retry logic for better consistency
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add a small delay between attempts to avoid rate limiting
                if attempt > 0:
                    import time
                    time.sleep(1)
                
                response = self.session.get(
                    f"{self.base_url}/jobs/view/{job_id}", timeout=10
                )
                response.raise_for_status()
                
                if "linkedin.com/signup" in response.url:
                    log.warning(f"Job {job_id}: Redirected to signup page")
                    continue
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Check if we got the full page content by looking for the applyUrl element
                code_element = soup.find("code", id="applyUrl")
                if not code_element and attempt < max_retries - 1:
                    log.warning(f"Job {job_id}: Attempt {attempt + 1} - No applyUrl element found, retrying...")
                    continue
                
                # If we get here, we have a valid response
                break
                
            except Exception as e:
                log.warning(f"Job {job_id}: Attempt {attempt + 1} failed - {str(e)}")
                if attempt == max_retries - 1:
                    log.error(f"Job {job_id}: All attempts failed, returning empty details")
                    return {}
                continue
        else:
            # If we exit the loop without breaking, all attempts failed
            return {}

        div_content = soup.find(
            "div", class_=lambda x: x and "show-more-less-html__markup" in x
        )
        description = None
        if div_content is not None:
            div_content = remove_attributes(div_content)
            description = div_content.prettify(formatter="html")
            if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
            elif self.scraper_input.description_format == DescriptionFormat.PLAIN:
                description = plain_converter(description)
        h3_tag = soup.find(
            "h3", text=lambda text: text and "Job function" in text.strip()
        )

        job_function = None
        if h3_tag:
            job_function_span = h3_tag.find_next(
                "span", class_="description__job-criteria-text"
            )
            if job_function_span:
                job_function = job_function_span.text.strip()

        company_logo = (
            logo_image.get("data-delayed-url")
            if (logo_image := soup.find("img", {"class": "artdeco-entity-image"}))
            else None
        )
        
        # Extract direct URL with retry logic
        job_url_direct = self._parse_job_url_direct_with_retry(soup, job_id)
        
        # Detect if this is an easy apply job from the job page
        is_easy_apply = self._is_easy_apply_job_from_page(soup)
        
        # Filter out easy apply jobs if requested
        if self.scraper_input.easy_apply is False and is_easy_apply:
            log.info(f"Job {job_id}: Filtering out easy apply job")
            return None  # Return None to skip this job
        
        return {
            "description": description,
            "job_level": parse_job_level(soup),
            "company_industry": parse_company_industry(soup),
            "job_type": parse_job_type(soup),
            "job_url_direct": job_url_direct,
            "company_logo": company_logo,
            "job_function": job_function,
            "is_easy_apply": is_easy_apply,
        }

    def _get_location(self, metadata_card: Optional[Tag]) -> Location:
        """
        Extracts the location data from the job metadata card.
        :param metadata_card
        :return: location
        """
        location = Location(country=Country.from_string(self.country))
        if metadata_card is not None:
            location_tag = metadata_card.find(
                "span", class_="job-search-card__location"
            )
            location_string = location_tag.text.strip() if location_tag else "N/A"
            parts = location_string.split(", ")
            if len(parts) == 2:
                city, state = parts
                location = Location(
                    city=city,
                    state=state,
                    country=Country.from_string(self.country),
                )
            elif len(parts) == 3:
                city, state, country = parts
                country = Country.from_string(country)
                location = Location(city=city, state=state, country=country)
        return location

    def _parse_job_url_direct(self, soup: BeautifulSoup) -> str | None:
        """
        Gets the job url direct from job page
        :param soup:
        :return: str
        """
        job_url_direct = None
        
        # Method 1: Look for code element with id="applyUrl"
        job_url_direct_content = soup.find("code", id="applyUrl")
        if job_url_direct_content:
            # Handle both regular content and HTML comments
            content = job_url_direct_content.decode_contents().strip()
            
            # If content is empty, just whitespace, or contains only HTML comments, 
            # try to get the raw string including comments
            if not content or content.isspace() or content.startswith('<!--'):
                content = str(job_url_direct_content)
                # Extract content from HTML comments if present
                comment_pattern = re.compile(r'<!--(.*?)-->', re.DOTALL)
                comment_match = comment_pattern.search(content)
                if comment_match:
                    content = comment_match.group(1).strip()
            # Try multiple regex patterns for better URL extraction
            patterns = [
                self.job_url_direct_regex,  # Original pattern: (?<=\?url=)[^"]+
                re.compile(r'(?<=url=)[^"&\s]+'),  # Alternative pattern: (?<=url=)[^"&\s]+
                re.compile(r'"(https?://[^"]+)"'),  # Direct URL in quotes: "(https?://[^"]+)"
                re.compile(r'url=([^"&\s]+)'),  # Pattern for url=encoded_url format
                re.compile(r'https?://[^\s"<>]+'),  # Any HTTP/HTTPS URL
            ]
            
            for pattern in patterns:
                job_url_direct_match = pattern.search(content)
                if job_url_direct_match:
                    # Handle different group patterns
                    if pattern.groups > 0:
                        job_url_direct = job_url_direct_match.group(1)
                    else:
                        job_url_direct = job_url_direct_match.group()
                    
                    job_url_direct = unquote(job_url_direct)
                    
                    # Skip LinkedIn internal URLs
                    if any(x in job_url_direct.lower() for x in ['linkedin.com', 'signup', 'login']):
                        continue
                    
                    # Clean up the URL - remove any trailing parameters that might be LinkedIn-specific
                    if '&urlHash=' in job_url_direct:
                        job_url_direct = job_url_direct.split('&urlHash=')[0]
                    
                    return job_url_direct
        
        # Method 2: Look for script tags containing applyUrl
        script_tags = soup.find_all("script")
        for script in script_tags:
            if script.string and "applyUrl" in script.string:
                patterns = [
                    self.job_url_direct_regex,  # Original pattern: (?<=\?url=)[^"]+
                    re.compile(r'(?<=url=)[^"&\s]+'),  # Alternative pattern: (?<=url=)[^"&\s]+
                    re.compile(r'"(https?://[^"]+)"'),  # Direct URL in quotes: "(https?://[^"]+)"
                    re.compile(r'url=([^"&\s]+)'),  # Pattern for url=encoded_url format
                    re.compile(r'https?://[^\s"<>]+'),  # Any HTTP/HTTPS URL
                ]
                
                for pattern in patterns:
                    job_url_direct_match = pattern.search(script.string)
                    if job_url_direct_match:
                        # Handle different group patterns
                        if pattern.groups > 0:
                            job_url_direct = job_url_direct_match.group(1)
                        else:
                            job_url_direct = job_url_direct_match.group()
                        
                        job_url_direct = unquote(job_url_direct)
                        
                        # Skip LinkedIn internal URLs
                        if any(x in job_url_direct.lower() for x in ['linkedin.com', 'signup', 'login']):
                            continue
                        
                        # Clean up the URL
                        if '&urlHash=' in job_url_direct:
                            job_url_direct = job_url_direct.split('&urlHash=')[0]
                        
                        return job_url_direct
        
        # Method 3: Look for any element containing applyUrl in data attributes
        elements_with_apply_url = soup.find_all(attrs={"data-apply-url": True})
        if elements_with_apply_url:
            job_url_direct = elements_with_apply_url[0].get("data-apply-url")
            if job_url_direct:
                return job_url_direct
        
        # Method 4: Look for external apply links in the page
        apply_links = soup.find_all("a", href=True)
        for link in apply_links:
            href = link.get("href", "")
            # Check if it's an external apply link (not LinkedIn)
            if (href and 
                not href.startswith("https://www.linkedin.com") and 
                not href.startswith("/legal/") and 
                not href.startswith("/jobs/") and
                not "linkedin.com" in href and
                not "user-agreement" in href and
                not "sign-in" in href and
                not "auth-button" in href and
                "apply" in href.lower()):
                job_url_direct = href
                return job_url_direct

        return job_url_direct

    def _parse_job_url_direct_with_retry(self, soup: BeautifulSoup, job_id: str) -> str | None:
        """
        Parse job URL direct with retry logic for better consistency
        :param soup: BeautifulSoup object of the job page
        :param job_id: Job ID for logging
        :return: Direct URL or None
        """
        # First try the normal method
        direct_url = self._parse_job_url_direct(soup)
        
        if direct_url:
            log.debug(f"Job {job_id}: Direct URL found on first attempt: {direct_url}")
            return direct_url
        
        # If no direct URL found, try refreshing the page and parsing again
        log.warning(f"Job {job_id}: No direct URL found, attempting retry...")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Add a small delay
                import time
                time.sleep(0.5)
                
                # Fetch the page again
                response = self.session.get(
                    f"{self.base_url}/jobs/view/{job_id}", timeout=10
                )
                
                if response.status_code == 200 and "linkedin.com/signup" not in response.url:
                    soup_retry = BeautifulSoup(response.text, "html.parser")
                    direct_url_retry = self._parse_job_url_direct(soup_retry)
                    
                    if direct_url_retry:
                        log.info(f"Job {job_id}: Direct URL found on retry attempt {attempt + 1}: {direct_url_retry}")
                        return direct_url_retry
                    else:
                        log.warning(f"Job {job_id}: Retry attempt {attempt + 1} - still no direct URL found")
                else:
                    log.warning(f"Job {job_id}: Retry attempt {attempt + 1} - failed to fetch page")
                    
            except Exception as e:
                log.warning(f"Job {job_id}: Retry attempt {attempt + 1} failed - {str(e)}")
        
        log.warning(f"Job {job_id}: All retry attempts failed, no direct URL found")
        return None

    def _is_easy_apply_job_from_page(self, soup: BeautifulSoup) -> bool:
        """
        Detects if a job is an easy apply job by looking for specific indicators in the job page
        :param soup: BeautifulSoup object of the job page
        :return: bool
        """
        # Method 1: Look for explicit easy apply button in the job page
        easy_apply_button = soup.find("button", class_=lambda x: x and "easy-apply" in " ".join(x).lower())
        if easy_apply_button:
            return True
            
        # Method 2: Look for explicit easy apply text in buttons
        buttons = soup.find_all("button")
        for button in buttons:
            text = button.get_text().lower().strip()
            if any(indicator in text for indicator in ["easy apply", "quick apply"]):
                return True
                
        # Method 3: Look for easy apply in data attributes
        if soup.find(attrs={"data-easy-apply": True}):
            return True
        
        # Method 4: Look for easy apply in class names
        if soup.find(class_=lambda x: x and "easy-apply" in " ".join(x).lower()):
            return True
            
        # Method 5: Check if there's an external apply URL - if yes, it's NOT easy apply
        apply_url_element = soup.find("code", id="applyUrl")
        if apply_url_element:
            content = apply_url_element.decode_contents().strip()
            if content and not any(x in content.lower() for x in ['linkedin.com', 'signup', 'login']):
                # Has external URL, so it's NOT easy apply
                return False
        
        # Method 5b: Also check script tags for applyUrl
        script_tags = soup.find_all("script")
        for script in script_tags:
            if script.string and "applyUrl" in script.string:
                # Look for external URLs in the script
                import re
                url_patterns = [
                    r'"(https?://[^"]+)"',
                    r'url=([^"&\s]+)',
                    r'https?://[^\s"<>]+'
                ]
                for pattern in url_patterns:
                    matches = re.findall(pattern, script.string)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match else ""
                        if match and not any(x in match.lower() for x in ['linkedin.com', 'signup', 'login']):
                            # Found external URL, so it's NOT easy apply
                            return False
        
        # Method 6: Look for external apply links in the page
        apply_links = soup.find_all("a", href=True)
        for link in apply_links:
            href = link.get("href", "")
            # Check if it's an external apply link (not LinkedIn)
            if (href and 
                not href.startswith("https://www.linkedin.com") and 
                not href.startswith("/legal/") and 
                not href.startswith("/jobs/") and
                not "linkedin.com" in href and
                not "user-agreement" in href and
                not "sign-in" in href and
                not "auth-button" in href and
                "apply" in href.lower()):
                # Found external apply link, so it's NOT easy apply
                return False
        
        # If we get here, we couldn't find explicit easy apply indicators
        # and we couldn't find external apply links
        # Be more conservative - only filter out if we have strong evidence it's easy apply
        # Look for additional indicators that suggest it's definitely an easy apply job
        
        # Check for LinkedIn-specific apply patterns that indicate easy apply
        page_text = soup.get_text().lower()
        
        # First check for explicit easy apply indicators
        explicit_easy_apply_indicators = [
            'easy apply',
            'quick apply', 
            'one-click apply',
            'apply with linkedin',
            'linkedin apply'
        ]
        
        if any(indicator in page_text for indicator in explicit_easy_apply_indicators):
            return True
        
        # For sign-in required patterns, be more careful - only filter out if we also
        # can't find any external apply URLs
        signin_indicators = [
            'join or sign in to find your next job',
            'sign in to find your next job',
            'join to apply for',
            'security verification',
            'already on linkedin? sign in'
        ]
        
        has_signin_indicators = any(indicator in page_text for indicator in signin_indicators)
        
        if has_signin_indicators:
            # Look for external apply URLs more thoroughly before deciding
            external_urls_found = False
            
            # Import re if not already imported
            import re
            
            # First, check if we already found external apply links in the earlier methods
            # (This is the most reliable indicator)
            apply_links = soup.find_all("a", href=True)
            for link in apply_links:
                href = link.get("href", "")
                if (href and
                    not href.startswith("https://www.linkedin.com") and
                    not href.startswith("/legal/") and
                    not href.startswith("/jobs/") and
                    not "linkedin.com" in href and
                    not "user-agreement" in href and
                    not "sign-in" in href and
                    not "auth-button" in href and
                    "apply" in href.lower()):
                    external_urls_found = True
                    break
            
            # If no external apply links found, check for any external URLs that might be apply URLs
            if not external_urls_found:
                # Check for external URLs in the page
                external_url_pattern = r'https://(?!www\.linkedin\.com)[^"\s<>]+'
                external_urls = re.findall(external_url_pattern, str(soup))
                
                # Filter out common non-apply URLs (be more specific to avoid filtering legitimate job URLs)
                non_apply_patterns = [
                    # LinkedIn non-job URLs
                    r'linkedin\.com/in/',
                    r'linkedin\.com/feed/',
                    r'linkedin\.com/messaging/',
                    r'linkedin\.com/notifications/',
                    r'media\.licdn\.com',
                    r'static\.licdn\.com',
                    r'cdn\.linkedin\.com',
                    
                    # Social media non-job URLs (but allow careers/jobs pages)
                    r'facebook\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                    r'twitter\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                    r'youtube\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                    r'instagram\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                    
                    # File extensions (definitely not job URLs)
                    r'\.css$',
                    r'\.js$',
                    r'\.png$',
                    r'\.jpg$',
                    r'\.jpeg$',
                    r'\.gif$',
                    r'\.svg$',
                    r'\.ico$',
                    r'\.pdf$',
                    r'\.zip$',
                    r'\.mp4$',
                    r'\.mp3$',
                    
                    # Common non-job page patterns
                    r'/legal/',
                    r'/privacy',
                    r'/terms',
                    r'/about$',
                    r'/contact$',
                    r'/news$',
                    r'/blog$',
                    r'/press$',
                    r'/investors$',
                    r'/help$',
                    r'/support$'
                ]
                
                for url in external_urls:
                    # Skip if it matches non-apply patterns
                    if any(re.search(pattern, url, re.IGNORECASE) for pattern in non_apply_patterns):
                        continue
                    
                    # If it's an external URL that doesn't match non-apply patterns,
                    # it could be an apply URL
                    external_urls_found = True
                    break
            
            # Only filter out if we have sign-in indicators AND no external URLs found
            if not external_urls_found:
                return True
        
        # Method 8: NEW - Check for jobs with Apply buttons but no external apply URLs
        # This is a strong indicator of Easy Apply jobs
        import re
        apply_buttons = soup.find_all(['button', 'a'], string=re.compile(r'apply', re.I))
        if apply_buttons and not apply_url_element:
            # If there are apply buttons but no applyUrl element, it's likely Easy Apply
            # unless we can find external apply URLs elsewhere
            external_urls_found = False
            
            # Check for any external URLs that might be apply URLs
            external_url_pattern = r'https://(?!www\.linkedin\.com)[^"\s<>]+'
            external_urls = re.findall(external_url_pattern, str(soup))

            # Filter out common non-apply URLs
            non_apply_patterns = [
                # LinkedIn non-job URLs
                r'linkedin\.com/in/',
                r'linkedin\.com/feed/',
                r'linkedin\.com/messaging/',
                r'linkedin\.com/notifications/',
                r'media\.licdn\.com',
                r'static\.licdn\.com',
                r'cdn\.linkedin\.com',
                
                # Social media non-job URLs (but allow careers/jobs pages)
                r'facebook\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                r'twitter\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                r'youtube\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                r'instagram\.com/(?!.*careers?)(?!.*jobs?)(?!.*work)',
                
                # File extensions (definitely not job URLs)
                r'\.css$',
                r'\.js$',
                r'\.png$',
                r'\.jpg$',
                r'\.jpeg$',
                r'\.gif$',
                r'\.svg$',
                r'\.ico$',
                r'\.pdf$',
                r'\.zip$',
                r'\.mp4$',
                r'\.mp3$',
                
                # Common non-job page patterns
                r'/legal/',
                r'/privacy',
                r'/terms',
                r'/about$',
                r'/contact$',
                r'/news$',
                r'/blog$',
                r'/press$',
                r'/investors$',
                r'/help$',
                r'/support$'
            ]
            
            for url in external_urls:
                # Skip if it matches non-apply patterns
                if any(re.search(pattern, url, re.IGNORECASE) for pattern in non_apply_patterns):
                    continue
                external_urls_found = True
                break

            # If no external URLs found, it's likely Easy Apply
            if not external_urls_found:
                return True

        # If no clear indicators either way, be conservative and don't filter
        return False

    def _is_easy_apply_job(self, job_card: Tag) -> bool:
        """
        Legacy method - kept for backward compatibility but no longer used for filtering
        Detects if a job is an easy apply job by looking for specific indicators in the job card
        :param job_card: BeautifulSoup element containing job card
        :return: bool
        """
        # This method is no longer used for filtering since easy apply detection
        # is now done at the job page level for better accuracy
        return False

    def _parse_relative_date(self, metadata_card) -> Optional[date]:
        """
        Parse relative date strings like "2 days ago", "1 week ago", etc.
        :param metadata_card: BeautifulSoup element containing metadata
        :return: date object or None
        """
        if not metadata_card:
            return None
            
        # Look for text that might contain relative dates
        text_content = metadata_card.get_text().lower()
        
        # Common relative date patterns
        import re
        from datetime import timedelta
        
        today = datetime.now().date()
        
        # Pattern for "X days ago"
        days_match = re.search(r'(\d+)\s+days?\s+ago', text_content)
        if days_match:
            days = int(days_match.group(1))
            return today - timedelta(days=days)
        
        # Pattern for "X weeks ago"
        weeks_match = re.search(r'(\d+)\s+weeks?\s+ago', text_content)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return today - timedelta(weeks=weeks)
        
        # Pattern for "X months ago"
        months_match = re.search(r'(\d+)\s+months?\s+ago', text_content)
        if months_match:
            months = int(months_match.group(1))
            # Approximate months as 30 days
            return today - timedelta(days=months * 30)
        
        # Pattern for "X years ago"
        years_match = re.search(r'(\d+)\s+years?\s+ago', text_content)
        if years_match:
            years = int(years_match.group(1))
            # Approximate years as 365 days
            return today - timedelta(days=years * 365)
        
        # Pattern for "yesterday"
        if 'yesterday' in text_content:
            return today - timedelta(days=1)
        
        # Pattern for "today"
        if 'today' in text_content:
            return today
        
        # Look for any time element that might have relative text
        time_elements = metadata_card.find_all("time")
        for time_elem in time_elements:
            time_text = time_elem.get_text().lower()
            if any(keyword in time_text for keyword in ['ago', 'yesterday', 'today']):
                # Try to parse this specific time element
                return self._parse_relative_date_from_text(time_text)
        
        return None
    
    def _parse_relative_date_from_text(self, text: str) -> Optional[date]:
        """
        Parse relative date from a specific text string
        :param text: text containing relative date
        :return: date object or None
        """
        import re
        from datetime import timedelta
        
        today = datetime.now().date()
        text = text.lower().strip()
        
        # Pattern for "X days ago"
        days_match = re.search(r'(\d+)\s+days?\s+ago', text)
        if days_match:
            days = int(days_match.group(1))
            return today - timedelta(days=days)
        
        # Pattern for "X weeks ago"
        weeks_match = re.search(r'(\d+)\s+weeks?\s+ago', text)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return today - timedelta(weeks=weeks)
        
        # Pattern for "X months ago"
        months_match = re.search(r'(\d+)\s+months?\s+ago', text)
        if months_match:
            months = int(months_match.group(1))
            return today - timedelta(days=months * 30)
        
        # Pattern for "X years ago"
        years_match = re.search(r'(\d+)\s+years?\s+ago', text)
        if years_match:
            years = int(years_match.group(1))
            return today - timedelta(days=years * 365)
        
        # Pattern for "yesterday"
        if 'yesterday' in text:
            return today - timedelta(days=1)
        
        # Pattern for "today"
        if 'today' in text:
            return today
        
        return None

