import json
import re
import html
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict, Any
from bs4 import BeautifulSoup

from jobspy_enhanced.model import (
    JobPost,
    Location,
    JobType,
    Compensation,
    CompensationInterval,
)
from jobspy_enhanced.util import (
    extract_emails_from_text,
    markdown_converter,
)
from jobspy_enhanced.dice.constant import SKILL_JUNK_RE

def clean_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace('\\/', '/').replace('\\u002F', '/').replace('\\u0026', '&').replace('\\"', '"').replace('\\\\', '\\')
    url = url.split('?')[0].split('#')[0]
    return re.sub(r'[\\"].*$', '', url).strip()

def extract_apply_url_from_job_data(job_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract apply URL from parsed job data (e.g. from __NEXT_DATA__).
    Prefer applyUrl / externalApplyUrl / directApplyUrl; return only non-Dice URLs.
    """
    if not job_data or not isinstance(job_data, dict):
        return None
    for key in ("applyUrl", "externalApplyUrl", "directApplyUrl", "applicationUrl", "apply_url", "external_apply_url"):
        url = job_data.get(key)
        if url and isinstance(url, str):
            url = clean_url(url.strip())
            if url.startswith("http") and "dice.com" not in url.lower():
                return url
    if "jobPosting" in job_data and isinstance(job_data["jobPosting"], dict):
        found = extract_apply_url_from_job_data(job_data["jobPosting"])
        if found:
            return found
    return None


def extract_apply_type_from_page(job_data: Optional[Dict[str, Any]], raw_html: str = "") -> Optional[str]:
    """
    Extract applyType from page source (component "applyType").
    Returns "EASY_APPLY", "EXTERNAL", or None. Normalizes common variants.
    """
    # From structured job_data (e.g. __NEXT_DATA__)
    if job_data and isinstance(job_data, dict):
        for key in ("applyType", "apply_type", "applicationType", "application_type"):
            val = job_data.get(key)
            if val and isinstance(val, str):
                v = val.strip().upper()
                if v in ("EASY_APPLY", "EASYAPPLY", "INTERNAL", "DICE"):
                    return "EASY_APPLY"
                if v in ("EXTERNAL", "EXTERNAL_APPLY", "COMPANY_SITE", "REDIRECT"):
                    return "EXTERNAL"
                if "EASY" in v or "INTERNAL" in v:
                    return "EASY_APPLY"
                if "EXTERNAL" in v or "REDIRECT" in v:
                    return "EXTERNAL"
        if "jobPosting" in job_data and isinstance(job_data["jobPosting"], dict):
            found = extract_apply_type_from_page(job_data["jobPosting"], "")
            if found:
                return found
    # From raw HTML / script (e.g. "applyType":"EXTERNAL")
    if raw_html:
        m = re.search(
            r'"applyType"\s*:\s*"(EASY_APPLY|EXTERNAL|EASYAPPLY|INTERNAL|EXTERNAL_APPLY|COMPANY_SITE|REDIRECT|[^"]+)"',
            raw_html,
            re.I,
        )
        if m:
            v = m.group(1).strip().upper()
            if v in ("EASY_APPLY", "EASYAPPLY", "INTERNAL", "DICE") or "EASY" in v or "INTERNAL" in v:
                return "EASY_APPLY"
            if v in ("EXTERNAL", "EXTERNAL_APPLY", "COMPANY_SITE", "REDIRECT") or "EXTERNAL" in v or "REDIRECT" in v:
                return "EXTERNAL"
    return None


def find_career_url_in_dict(obj: Any) -> Optional[str]:
    career_patterns = ['workday', 'taleo', 'greenhouse', 'lever', 'icims', 'myworkday', 'salesforce.wd12', 'jobvite', 'smartrecruiters']
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and any(p in value.lower() for p in career_patterns) and 'http' in value:
                m = re.search(r'(https?://[^\s"\'<>]+)', value)
                if m:
                    url = clean_url(m.group(1))
                    if 'dice.com' not in url:
                        return url
            elif isinstance(value, (dict, list)):
                result = find_career_url_in_dict(value)
                if result:
                    return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_career_url_in_dict(item)
            if result:
                return result
    return None

def extract_employment_type_from_raw_html(raw_html: str) -> Optional[str]:
    if not raw_html:
        return None
    patterns = [
        r'"employmentType"\s*:\s*"([^"]+)"',
        r'\\"employmentType\\"\s*:\s*\\"([^\\]+)\\"',
        r'"employment_type"\s*:\s*"([^"]+)"',
        r'\\"employment_type\\"\s*:\s*\\"([^\\]+)\\"',
        r'"jobType"\s*:\s*"([^"]+)"',
        r'\\"jobType\\"\s*:\s*\\"([^\\]+)\\"',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_html, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None

def extract_apply_url_from_raw_html(raw_html: str) -> Optional[str]:
    """Extract apply URL from raw HTML. Prefer applyUrl/externalApplyUrl/directApplyUrl; never return dice.com."""
    if not raw_html:
        return None
    # First: explicit applyUrl-style keys – accept any non-Dice URL from these
    patterns = [
        r'"applyUrl"\s*:\s*"(https?://[^"]+?)"',
        r'\\"applyUrl\\":\s*\\"(https?://[^\\]+?)\\"',
        r'"externalApplyUrl"\s*:\s*"(https?://[^"]+?)"',
        r'\\"externalApplyUrl\\":\s*\\"(https?://[^\\]+?)\\"',
        r'"directApplyUrl"\s*:\s*"(https?://[^"]+?)"',
        r'\\"directApplyUrl\\":\s*\\"(https?://[^\\]+?)\\"',
    ]
    for pattern in patterns:
        for match in re.findall(pattern, raw_html):
            url = match.strip().replace('\\/', '/').replace('\\u002F', '/').replace('\\u0026', '&').replace('\\"', '"').replace('\\\\', '\\')
            url = re.sub(r'[\\"].*$', '', url)
            if url.startswith('http') and 'dice.com' not in url.lower():
                return url
    # Fallback: career-domain or generic applyUrl-like patterns
    career_domains = ['workday', 'myworkday', 'taleo', 'greenhouse', 'lever', 'icims', 'jobvite', 'smartrecruiters', 'breezy', 'bamboohr', 'applytojob', 'recruiting', 'careers', 'jobs', 'wd1.', 'wd5.', 'wd12.', 'employment']
    for url in re.findall(r'applyUrl[^h]*?(https?://[^"\s\\]+)', raw_html, re.IGNORECASE):
        url = url.replace('\\/', '/').replace('\\u002F', '/').replace('\\u0026', '&')
        url = re.sub(r'[\\"].*$', '', url)
        if url.startswith('http') and 'dice.com' not in url.lower():
            if any(d in url.lower() for d in career_domains) or len(url) > 30:
                return url
    career_url_pattern = r'(https?://(?:www\.)?(?:[a-zA-Z0-9-]+\.)?(?:workday|myworkday|taleo|greenhouse|lever|icims|jobvite|smartrecruiters)[^"\s<>]+)'
    for url in re.findall(career_url_pattern, raw_html, re.IGNORECASE):
        url = url.replace('\\/', '/').replace('\\u002F', '/').replace('\\u0026', '&')
        url = re.sub(r'[\\"].*$', '', url)
        if url.startswith('http') and 'dice.com' not in url:
            return url
    return None

def clean_description(description: str) -> str:
    if not description:
        return ""
    try:
        description = description.encode().decode('unicode_escape')
    except:
        pass
    description = html.unescape(description)
    description = re.sub(r'<br\s*/?\s*>', '\n', description, flags=re.IGNORECASE)
    description = re.sub(r'<[^>]+>', '', description)
    description = re.sub(r'\n{3,}', '\n\n', description)
    description = re.sub(r' {2,}', ' ', description)
    return description.strip()

def extract_salary_from_description(description: str) -> Optional[Compensation]:
    if not description:
        return None
    hourly_patterns = [
        r'\$\s*([\d,.]+)\s*(?:-|to|–|—)\s*\$?\s*([\d,.]+)\s*(?:per\s*hour|\/\s*hour|hourly|\/\s*hr|\bph\b|an\s*hour)',
        r'\$\s*([\d,.]+)\s*(?:per\s*hour|\/\s*hour|hourly|\/\s*hr|\bph\b|an\s*hour)',
        r'(?:hourly|rate|pay)\s*:?\s*\$\s*([\d,.]+)\s*(?:/hr|per\s*hour)?',
    ]
    for pattern in hourly_patterns:
        for match in re.finditer(pattern, description, re.IGNORECASE):
            try:
                groups = match.groups()
                min_val = float(groups[0].replace(',', ''))
                max_val = float(groups[1].replace(',', '')) if len(groups) >= 2 and groups[1] else min_val
                if 8 <= min_val <= 300 and 8 <= max_val <= 300 and min_val <= max_val:
                    return Compensation(interval=CompensationInterval.HOURLY, min_amount=min_val, max_amount=max_val, currency='USD')
            except (ValueError, IndexError, AttributeError):
                continue
    k_patterns = [
        r'\$\s*([\d,.]+)\s*[kK]\s*(?:-|to|–|—)\s*\$?\s*([\d,.]+)\s*[kK]',
        r'(?<!\$)\b([\d,.]+)\s*[kK]\s*(?:-|to|–|—)\s*([\d,.]+)\s*[kK]\b',
        r'(?:salary|compensation|pay|rate|base|annual)\s*:?\s*\$?\s*([\d,.]+)\s*[kK]\b',
        r'\$\s*([\d,.]+)\s*[kK]\b',
    ]
    for pattern in k_patterns:
        for match in re.finditer(pattern, description, re.IGNORECASE):
            try:
                groups = match.groups()
                min_val = int(float(groups[0].replace(',', '')) * 1000)
                max_val = int(float(groups[1].replace(',', '')) * 1000) if len(groups) >= 2 and groups[1] else min_val
                if 20000 <= min_val <= 800000 and 20000 <= max_val <= 800000 and min_val <= max_val:
                    return Compensation(interval=CompensationInterval.YEARLY, min_amount=min_val, max_amount=max_val, currency='USD')
            except (ValueError, IndexError, AttributeError):
                continue
    annual_context_patterns = [
        r'(?:salary|compensation|pay)\s*(?:range|is|of)?\s*:?\s*\$\s*([\d,]+)\s*(?:-|to|–|—)\s*\$?\s*([\d,]+)',
        r'(?:base|annual|yearly)\s*(?:salary|compensation|pay)\s*:?\s*\$\s*([\d,]+)',
        r'\$\s*([\d,]+)\s*(?:-|to|–|—)\s*\$?\s*([\d,]+)\s*(?:annually|per\s*year|\/\s*year|yearly|a\s*year|\/yr)',
        r'\$\s*([\d,]+)\s*(?:annually|per\s*year|\/\s*year|yearly|a\s*year|\/yr)',
    ]
    for pattern in annual_context_patterns:
        for match in re.finditer(pattern, description, re.IGNORECASE):
            try:
                groups = match.groups()
                min_val = int(groups[0].replace(',', ''))
                max_val = int(groups[1].replace(',', '')) if len(groups) >= 2 and groups[1] else min_val
                if 15000 <= min_val <= 1500000 and 15000 <= max_val <= 1500000 and min_val <= max_val:
                    return Compensation(interval=CompensationInterval.YEARLY, min_amount=min_val, max_amount=max_val, currency='USD')
            except (ValueError, IndexError, AttributeError):
                continue
    for match in re.finditer(r'\$\s*([\d,]+)\s*(?:-|to|–|—)\s*\$?\s*([\d,]+)(?!\s*(?:per\s*hour|\/\s*hr|hourly|ph\b))', description, re.IGNORECASE):
        try:
            min_val = int(match.group(1).replace(',', ''))
            max_val = int(match.group(2).replace(',', ''))
            if 25000 <= min_val <= 800000 and 25000 <= max_val <= 800000 and min_val < max_val and (max_val - min_val) >= 5000:
                return Compensation(interval=CompensationInterval.YEARLY, min_amount=min_val, max_amount=max_val, currency='USD')
        except (ValueError, IndexError):
            continue
    match = re.search(r'\$\s*([\d,]+)\s*(?:per\s*year|\/\s*year|yearly|annually)', description, re.IGNORECASE)
    if match:
        try:
            val = int(match.group(1).replace(',', ''))
            if 15000 <= val <= 1500000:
                return Compensation(interval=CompensationInterval.YEARLY, min_amount=val, max_amount=val, currency='USD')
        except (ValueError, IndexError):
            pass
    return None

def extract_experience_from_description(description: str) -> Optional[str]:
    if not description:
        return None
    word_to_num = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'twenty': 20, 'thirty': 30}
    p = re.search(r'(\d+)\s*\+\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp\b|professional|work|relevant|related)', description, re.IGNORECASE)
    if p: return f"{p.group(1)}+ years"
    p = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp\b|professional|work|relevant|related)', description, re.IGNORECASE)
    if p: return f"{p.group(1)}-{p.group(2)} years"
    p = re.search(r'(?:minimum|minimum\s+of|at\s+least|atleast|require[sd]?)\s+(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp\b|professional|work|relevant|related)', description, re.IGNORECASE)
    if p: return f"{p.group(1)}+ years"
    p = re.search(r'(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp\b|professional\s+experience|work\s+experience|relevant\s+experience|related\s+experience)', description, re.IGNORECASE)
    if p: return f"{p.group(1)} years"
    p = re.search(r'(?:requirements?|qualifications?|skills?)[:\s]+.*?(\d+)\s*\+\s*(?:years?|yrs?)', description, re.IGNORECASE | re.DOTALL)
    if p: return f"{p.group(1)}+ years"
    p = re.search(r'\b(' + '|'.join(word_to_num.keys()) + r')\s+to\s+(' + '|'.join(word_to_num.keys()) + r')\s*(?:years?|yrs?)', description, re.IGNORECASE)
    if p:
        mn, mx = p.group(1).lower(), p.group(2).lower()
        if mn in word_to_num and mx in word_to_num:
            return f"{word_to_num[mn]}-{word_to_num[mx]} years"
    p = re.search(r'\b(' + '|'.join(word_to_num.keys()) + r')\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp\b)', description, re.IGNORECASE)
    if p:
        word = p.group(1).lower()
        if word in word_to_num:
            return f"{word_to_num[word]}+ years" if '+' in p.group(0) else f"{word_to_num[word]} years"
    return None

def is_valid_skill(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 60 or '$' in t:
        return False
    return not SKILL_JUNK_RE.search(t)

def extract_skills_from_html(soup: BeautifulSoup) -> Optional[List[str]]:
    skills = []
    skills_headings = soup.find_all(['h3', 'h4', 'div', 'span'], string=re.compile(r'^\s*skills?\s*$', re.IGNORECASE))
    for heading in skills_headings:
        next_elem = heading.find_next_sibling()
        if next_elem and next_elem.name in ['ul', 'ol']:
            for li in next_elem.find_all('li'):
                t = li.get_text(strip=True)
                if t and len(t) < 50:
                    skills.append(t)
        parent = heading.parent
        if parent:
            next_elem = parent.find_next_sibling()
            if next_elem and next_elem.name in ['ul', 'ol']:
                for li in next_elem.find_all('li'):
                    t = li.get_text(strip=True)
                    if t and len(t) < 50:
                        skills.append(t)
    skills_containers = []
    for heading in skills_headings:
        parent = heading.parent
        if parent:
            skills_containers.append(parent)
        grandparent = parent.parent if parent else None
        if grandparent:
            skills_containers.append(grandparent)
    for container in skills_containers:
        for badge in container.find_all(class_=re.compile(r'skill|badge|chip|tag', re.I)):
            t = badge.get_text(strip=True)
            if t and 2 < len(t) < 50 and t not in skills:
                skills.append(t)
        for badge in container.find_all(attrs={'data-testid': re.compile(r'skill', re.I)}):
            t = badge.get_text(strip=True)
            if t and 2 < len(t) < 50 and t not in skills:
                skills.append(t)
    unique_skills = []
    seen = set()
    for skill in skills:
        if not is_valid_skill(skill):
            continue
        k = skill.strip().lower()
        if k not in seen:
            seen.add(k)
            unique_skills.append(skill.strip())
    return unique_skills if unique_skills else None

def extract_skills_from_json(job_data: Dict[str, Any]) -> Optional[List[str]]:
    skills = []
    for field in ['skills', 'qualifications', 'requirements', 'skillTags', 'technologies']:
        val = job_data.get(field)
        if val:
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "name" in item:
                        skills.append(item["name"])
                    elif isinstance(item, str):
                        skills.append(item)
            elif isinstance(val, str):
                for s in re.split(r'[,\n•]', val):
                    s = s.strip()
                    if s and len(s) < 50 and not s.startswith('http'):
                        skills.append(s)
    if 'jobPosting' in job_data:
        for field in ['skills', 'qualifications', 'requirements', 'skillTags', 'technologies']:
            val = job_data['jobPosting'].get(field)
            if val:
                if isinstance(val, list):
                    skills.extend([str(s) for s in val if s])
                elif isinstance(val, str):
                    skills.extend([s.strip() for s in val.split(',') if s.strip()])
    unique_skills = []
    seen = set()
    for s in skills:
        if not isinstance(s, str) or not is_valid_skill(s):
            continue
        k = s.strip().lower()
        if k and k not in seen:
            seen.add(k)
            unique_skills.append(s.strip())
    return unique_skills if unique_skills else None

def extract_skills_from_text(text: str) -> Optional[List[str]]:
    if not text:
        return None
    skills = []
    common_skills = [
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'node', 'express', 'django', 'flask', 'spring', 'hibernate',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras',
        'data science', 'data analysis', 'pandas', 'numpy', 'scikit-learn',
        'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind',
        'c++', 'c#', '.net', 'php', 'ruby', 'go', 'rust', 'scala',
        'hadoop', 'spark', 'kafka', 'airflow', 'tableau', 'power bi'
    ]
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            skills.append(skill.title())
    for item in re.findall(r'[•\-]\s*([A-Za-z][A-Za-z\s]{2,30})', text):
        item = item.strip()
        if item and len(item) < 50 and item.lower() not in [s.lower() for s in skills]:
            skills.append(item)
    return [s for s in skills if is_valid_skill(s)] or None

def extract_from_next_data(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    next_data_script = soup.find('script', id='__NEXT_DATA__')
    if not next_data_script or not next_data_script.string:
        return None
    try:
        next_data = json.loads(next_data_script.string)
        if 'props' in next_data and 'pageProps' in next_data['props']:
            page_props = next_data['props']['pageProps']
            if 'jobData' in page_props:
                return page_props['jobData']
            if 'dehydratedState' in page_props and 'queries' in page_props['dehydratedState']:
                for query in page_props['dehydratedState']['queries']:
                    if query and 'state' in query and 'data' in query['state']:
                        data = query['state']['data']
                        if isinstance(data, dict):
                            if data.get('jobPosting'):
                                return data['jobPosting']
                            elif data.get('jobId') or data.get('id'):
                                return data
                            elif 'job' in data:
                                return data['job']
    except Exception:
        pass
    return None

def extract_structured_data(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                return data
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                        return item
        except:
            continue
    return None

def extract_base_salary_from_raw_html(raw_html: str) -> Optional[Compensation]:
    if not raw_html:
        return None
    try:
        m = re.search(r'"baseSalary"\s*:\s*(\{[^}]+\})', raw_html)
        if m:
            salary_json = json.loads(m.group(1))
            currency = salary_json.get('currency', 'USD')
            if 'minValue' in salary_json and 'maxValue' in salary_json:
                mn, mx = float(salary_json['minValue']), float(salary_json['maxValue'])
                if mn < 500 and mx < 500:
                    return Compensation(interval=CompensationInterval.HOURLY, min_amount=mn, max_amount=mx, currency=currency)
                return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(mn), max_amount=int(mx), currency=currency)
            elif 'value' in salary_json:
                if isinstance(salary_json['value'], dict):
                    mn = salary_json['value'].get('minValue')
                    mx = salary_json['value'].get('maxValue')
                    if mn and mx:
                        mn, mx = float(mn), float(mx)
                        if mn < 500 and mx < 500:
                            return Compensation(interval=CompensationInterval.HOURLY, min_amount=mn, max_amount=mx, currency=currency)
                        return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(mn), max_amount=int(mx), currency=currency)
                else:
                    val = float(salary_json['value'])
                    if val < 500:
                        return Compensation(interval=CompensationInterval.HOURLY, min_amount=val, max_amount=val, currency=currency)
                    return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(val), max_amount=int(val), currency=currency)
    except Exception:
        pass
    return None

def extract_salary_from_json(job_data: Dict[str, Any]) -> Optional[Compensation]:
    base_salary = job_data.get('baseSalary') or job_data.get('salary') or job_data.get('compensation')
    if not base_salary:
        return None
    currency = 'USD'
    if isinstance(base_salary, dict):
        currency = base_salary.get('currency', 'USD')
        if 'minValue' in base_salary and 'maxValue' in base_salary:
            mn, mx = float(base_salary['minValue']), float(base_salary['maxValue'])
            if mn < 500 and mx < 500:
                return Compensation(interval=CompensationInterval.HOURLY, min_amount=mn, max_amount=mx, currency=currency)
            return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(mn), max_amount=int(mx), currency=currency)
        elif 'minValue' in base_salary:
            val = float(base_salary['minValue'])
            if val < 500:
                return Compensation(interval=CompensationInterval.HOURLY, min_amount=val, max_amount=val, currency=currency)
            return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(val), max_amount=int(val), currency=currency)
        elif 'value' in base_salary:
            if isinstance(base_salary['value'], dict):
                mn = base_salary['value'].get('minValue')
                mx = base_salary['value'].get('maxValue')
                if mn and mx:
                    mn, mx = float(mn), float(mx)
                    if mn < 500 and mx < 500:
                        return Compensation(interval=CompensationInterval.HOURLY, min_amount=mn, max_amount=mx, currency=currency)
                    return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(mn), max_amount=int(mx), currency=currency)
            else:
                try:
                    val = float(base_salary['value'])
                    if val < 500:
                        return Compensation(interval=CompensationInterval.HOURLY, min_amount=val, max_amount=val, currency=currency)
                    return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(val), max_amount=int(val), currency=currency)
                except (ValueError, TypeError):
                    pass
    elif isinstance(base_salary, (int, float, str)):
        try:
            val = float(base_salary)
            if val < 500:
                return Compensation(interval=CompensationInterval.HOURLY, min_amount=val, max_amount=val, currency='USD')
            return Compensation(interval=CompensationInterval.YEARLY, min_amount=int(val), max_amount=int(val), currency='USD')
        except (ValueError, TypeError):
            pass
    return None

def parse_location(location_text: str) -> Optional[Location]:
    if not location_text:
        return None
    location_text = re.sub(r'^(location:?\s*|city:?\s*|in\s+)', '', location_text, flags=re.I)
    parts = [p.strip() for p in location_text.split(',')]
    if len(parts) >= 2:
        return Location(city=parts[0], state=parts[1], country=parts[2] if len(parts) > 2 else 'USA')
    return None

def parse_posted_date(date_text: str) -> Optional[str]:
    if not date_text:
        return None
    date_text = date_text.lower().strip()
    today = datetime.now()
    if 'today' in date_text:
        return today.strftime("%Y-%m-%d")
    elif 'yesterday' in date_text:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.search(r'(\d+)\s+days?\s+ago', date_text)
    if m:
        return (today - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    return None

def map_job_type(job_type_text: str) -> Optional[JobType]:
    if not job_type_text:
        return None
    t = job_type_text.lower()
    mapping = {
        'full time': JobType.FULL_TIME, 'full-time': JobType.FULL_TIME, 'full_time': JobType.FULL_TIME,
        'part time': JobType.PART_TIME, 'part-time': JobType.PART_TIME, 'part_time': JobType.PART_TIME,
        'contract': JobType.CONTRACT, 'contractor': JobType.CONTRACT,
        'internship': JobType.INTERNSHIP,
    }
    for key, value in mapping.items():
        if key in t:
            return value
    return None

# --- W2/C2C bucket constants (recommended buckets from phrase/tag rules) ---
W2_ONLY = "W2_ONLY"
W2_LIKELY = "W2_LIKELY"
C2C_ONLY = "C2C_ONLY"
C2C_ALLOWED = "C2C_ALLOWED"
W2_PREFERRED = "W2_PREFERRED"   # both W2 and C2C allowed, W2 listed first
C2C_PREFERRED = "C2C_PREFERRED"  # both W2 and C2C allowed, C2C listed first

ALL_BUCKETS = (W2_ONLY, W2_LIKELY, C2C_ONLY, C2C_ALLOWED, W2_PREFERRED, C2C_PREFERRED)


def bucket_to_legacy(bucket: Optional[str]) -> Optional[str]:
    """Map bucket to legacy is_c2c_or_w2 value: 'W2', 'C2C', or None."""
    if not bucket:
        return None
    if bucket in (W2_ONLY, W2_LIKELY, W2_PREFERRED):
        return "W2"
    if bucket in (C2C_ONLY, C2C_ALLOWED, C2C_PREFERRED):
        return "C2C"
    return None


# Phrase rules: (list of compiled regex, bucket). Order matters for priority.
# 1) Both-allowed (W2_PREFERRED / C2C_PREFERRED) — check first
_BOTH_W2_FIRST = [
    re.compile(r"\bw-?2\s+or\s+c-?2-?c\b", re.I),
    re.compile(r"\bw-?2\s*/\s*c-?2-?c\b", re.I),
    re.compile(r"\bopen\s+for\s+w-?2\s+and\s+c-?2-?c\b", re.I),
    re.compile(r"\bcontract\s+w-?2\s+or\s+c-?2-?c\b", re.I),
    re.compile(r"\bw-?2\s*/\s*1099\s*/\s*c-?2-?c\b", re.I),
]
_BOTH_C2C_FIRST = [
    re.compile(r"\bc-?2-?c\s*/\s*w-?2\b", re.I),
]
# 2) W2_ONLY (very high confidence)
_W2_ONLY_PATTERNS = [
    re.compile(r"\bw-?2\s+only\b", re.I),
    re.compile(r"\bonly\s+w-?2\b", re.I),
    re.compile(r"\bmust\s+be\s+w-?2\b", re.I),
    re.compile(r"\bw-?2\s+required\b", re.I),
    re.compile(r"\bw-?2\s+candidates\s+only\b", re.I),
    re.compile(r"\bcontract\s+w-?2\b", re.I),
    re.compile(r"\bno\s+c-?2-?c\b", re.I),
    re.compile(r"\bno\s+corp\s*[-]?\s*to\s*[-]?\s*corp\b", re.I),
    re.compile(r"\bcannot\s+work\s+corp\s*[-]?\s*to\s*[-]?\s*corp\b", re.I),
    re.compile(r"\bno\s+c-?2-?c\s+candidates\b", re.I),
    re.compile(r"\bno\s+c-?2-?c\s*/\s*no\s+1099\b", re.I),
    re.compile(r"\bcandidate\s+must\s+be\s+on\s+vendor\s+w-?2\b", re.I),
    re.compile(r"\bmust\s+work\s+on\s+our\s+w-?2\b", re.I),
    re.compile(r"\bonly\s+on\s+our\s+payroll\b", re.I),
    re.compile(r"\bvendor\s+w-?2\s+only\b", re.I),
    re.compile(r"\bon\s+w-?2\b", re.I),
    re.compile(r"\bon\s+a\s+w-?2\b", re.I),
    re.compile(r"\bw\s+2\b", re.I),
]
# 3) W2_LIKELY (high / medium) — includes contract-employment phrases that indicate W2
_W2_LIKELY_PATTERNS = [
    re.compile(r"\bno\s+third\s+part(y|ies)\b", re.I),
    re.compile(r"\bno\s+third\s*[-]?\s*party\s+vendors\b", re.I),
    re.compile(r"\bno\s+vendor\s+layers\b", re.I),
    re.compile(r"\bno\s+3rd\s+party\b", re.I),
    re.compile(r"\bno\s+third\s+party\s+candidates\b", re.I),
    re.compile(r"\bno\s+vendors\b", re.I),
    re.compile(r"\bno\s+implementation\s+partners\b", re.I),
    re.compile(r"\bno\s+layers\b", re.I),
    re.compile(r"\bdirect\s+candidate\s+only\b", re.I),
    re.compile(r"\bcandidate\s+must\s+be\s+on\s+our\s+payroll\b", re.I),
    re.compile(r"\bno\s+subcontractors\b", re.I),
    re.compile(r"\bno\s+subcontracting\b", re.I),
    re.compile(r"\bvendor\s+payroll\b", re.I),
    re.compile(r"\bemployer\s+of\s+record\b", re.I),
    # Contract employment phrases (contract to hire, contract position, etc.)
    re.compile(r"\bcontract\s+to\s+hire\b", re.I),
    re.compile(r"\bcontract\s+position\b", re.I),
    re.compile(r"\bcontract\s+role\b", re.I),
    re.compile(r"\bcontract\s+opportunity\b", re.I),
    re.compile(r"\bcontract\s+employment\b", re.I),
    re.compile(r"\bcontract\s+worker\b", re.I),
    re.compile(r"\bcontract\s+staff\b", re.I),
    re.compile(r"\bcontract\s+engagement\b", re.I),
    re.compile(r"\bcontract\s+job\b", re.I),
    re.compile(r"\bemployment\s+type\s*:\s*contract\b", re.I),
    re.compile(r"\bjob\s+type\s*:\s*contract\b", re.I),
    re.compile(r"\bcontractual\s+position\b", re.I),
    re.compile(r"\bcontractual\s+role\b", re.I),
    re.compile(r"\bcontractual\s+employment\b", re.I),
    re.compile(r"\bcontract\s+independent\b", re.I),
    re.compile(r"\b1099\b", re.I),
    re.compile(r"\bindependent\s+contractor\b", re.I),
]
# 4) C2C_ONLY (very high)
_C2C_ONLY_PATTERNS = [
    re.compile(r"\bc-?2-?c\s+only\b", re.I),
    re.compile(r"\bcorp\s*[-]?\s*to\s*[-]?\s*corp\s+only\b", re.I),
    re.compile(r"\bc-?2-?c\s+required\b", re.I),
    re.compile(r"\bcorp\s*2\s*corp\s+only\b", re.I),
    re.compile(r"\bcorporation\s+to\s+corporation\s+only\b", re.I),
    re.compile(r"\bcontract\s+corp\s*[-]?\s*to\s*[-]?\s*corp\b", re.I),
    re.compile(r"\bcorporation\s+to\s+corporation\b", re.I),
    re.compile(r"\b1099\s+only\b", re.I),
]
# 5) C2C_ALLOWED (medium) — after C2C_ONLY so "c2c only" wins; C2C keyword variants
_C2C_ALLOWED_PATTERNS = [
    re.compile(r"\bc-?2-?c\s+candidates\s+welcome\b", re.I),
    re.compile(r"\bopen\s+for\s+c-?2-?c\b", re.I),
    re.compile(r"\bc-?2-?c\s+acceptable\b", re.I),
    re.compile(r"\bc-?2-?c\s+ok\b", re.I),
    re.compile(r"\bc-?2-?c\s+accepted\b", re.I),
    re.compile(r"\bc-?2-?c\s+considered\b", re.I),
    re.compile(r"\bc-?2-?c\s+available\b", re.I),
    re.compile(r"\bcorp\s*[-]?\s*to\s*[-]?\s*corp\s+available\b", re.I),
    re.compile(r"\bcorp\s*[-]?\s*to\s*[-]?\s*corp\s+allowed\b", re.I),
    re.compile(r"\bcorp\s+-\s+to\s+-\s+corp\b", re.I),
    re.compile(r"\b1099\s+contract\b", re.I),
    re.compile(r"\bc-?2-?c\b", re.I),
    re.compile(r"\bc-2-c\b", re.I),
    re.compile(r"\bc\s*2\s*c\b", re.I),
    re.compile(r"\bcorp\s*[-]?\s*to\s*[-]?\s*corp\b", re.I),
    re.compile(r"\bcorp\s*2\s*corp\b", re.I),
    re.compile(r"\bcorporation\s+to\s+corporation\b", re.I),
]


def classify_w2_c2c_bucket(title: str, description: str, full_page_text: str = "") -> Optional[str]:
    """
    Classify W2/C2C bucket from title and description using the full phrase rule table.
    Returns one of: W2_ONLY, W2_LIKELY, C2C_ONLY, C2C_ALLOWED, W2_PREFERRED, C2C_PREFERRED, or None.
    Priority: both-allowed (W2/C2C preferred) > W2_ONLY > C2C_ONLY > W2_LIKELY > C2C_ALLOWED.
    """
    text = f"{title or ''} {description or ''} {full_page_text or ''}".lower()
    if not text.strip():
        return None
    # 1) Both C2C and W2 present — classify as C2C
    for p in _BOTH_C2C_FIRST:
        if p.search(text):
            return C2C_PREFERRED
    for p in _BOTH_W2_FIRST:
        if p.search(text):
            return C2C_PREFERRED
    # 2) W2_ONLY
    for p in _W2_ONLY_PATTERNS:
        if p.search(text):
            return W2_ONLY
    # 3) C2C_ONLY
    for p in _C2C_ONLY_PATTERNS:
        if p.search(text):
            return C2C_ONLY
    # 4) W2_LIKELY
    for p in _W2_LIKELY_PATTERNS:
        if p.search(text):
            return W2_LIKELY
    # 5) C2C_ALLOWED (generic c2c/corp to corp/1099)
    for p in _C2C_ALLOWED_PATTERNS:
        if p.search(text):
            return C2C_ALLOWED
    return None


def w2_c2c_from_employment_type(employment_type: Optional[str]) -> Optional[str]:
    """
    Map Dice employmentType (or raw) to W2/C2C bucket. Returns None if not C2C/W2.
    Contract W2 / W2 -> W2_ONLY; Contract Corp-To-Corp / CORP_TO_CORP / C2C -> C2C_ONLY.
    """
    if not employment_type or not isinstance(employment_type, str):
        return None
    t = employment_type.strip().lower()
    if not t:
        return None
    if "c2c" in t or re.search(r"corp\s*[-_]?\s*(2|to)\s*[-_]?\s*corp", t):
        return C2C_ONLY
    if "w2" in t or "w-2" in t:
        return W2_ONLY
    return None


def _collect_employment_type_candidates(job_data: Dict[str, Any], out: List[str]) -> None:
    """Recursively collect employment/contract type strings from job_data (including nested jobPosting)."""
    if not job_data or not isinstance(job_data, dict):
        return
    for key in ("employmentType", "employment_type", "workType", "work_type", "contractType", "contract_type"):
        val = job_data.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            out.append(val)
        elif isinstance(val, list):
            out.extend(str(v) for v in val if v)
    for key in ("employmentTypes", "employment_types", "workTypes", "work_types"):
        et_list = job_data.get(key)
        if isinstance(et_list, list):
            out.extend(str(v) for v in et_list if v)
    for nested_key in ("jobPosting", "job", "data", "jobData"):
        nested = job_data.get(nested_key)
        if isinstance(nested, dict):
            _collect_employment_type_candidates(nested, out)


def w2_c2c_from_job_data(job_data: Optional[Dict[str, Any]], employment_type_raw: Optional[str] = None) -> Optional[str]:
    """
    Resolve W2/C2C bucket from job_data employment type fields (and optional raw string).
    Checks employmentType, workType, contractType, etc., including nested jobPosting. W2 has priority when multiple.
    """
    candidates: List[str] = []
    if employment_type_raw and isinstance(employment_type_raw, str):
        candidates.append(employment_type_raw)
    if job_data and isinstance(job_data, dict):
        _collect_employment_type_candidates(job_data, candidates)
    w2_found = False
    c2c_found = False
    for s in candidates:
        res = w2_c2c_from_employment_type(s)
        if res == W2_ONLY:
            w2_found = True
        elif res == C2C_ONLY:
            c2c_found = True
    if w2_found:
        return W2_ONLY
    if c2c_found:
        return C2C_ONLY
    return None


def extract_w2_c2c_from_raw_html(raw_html: str) -> Optional[str]:
    """
    Extract W2 or C2C from Dice page raw HTML when structured job_data doesn't have it.
    Looks for employmentType/workType/contractType and C2C/W2 badge-like strings. Returns W2_ONLY, C2C_ONLY, or None.
    """
    if not raw_html:
        return None
    # Structured JSON-like values (Dice often embeds these)
    patterns_value = [
        (r'"(?:employmentType|workType|contractType|employment_type|work_type)"\s*:\s*"(Contract\s+Corp[^"]*Corp[^"]*)"', C2C_ONLY),
        (r'"(?:employmentType|workType|contractType|employment_type|work_type)"\s*:\s*"(CORP_TO_CORP|C2C|[^"]*c2c[^"]*)"', C2C_ONLY),
        (r'"(?:employmentType|workType|contractType|employment_type|work_type)"\s*:\s*"(Contract\s+W2|W2[^"]*)"', W2_ONLY),
        (r'"(?:employmentType|workType|contractType|employment_type|work_type)"\s*:\s*"([^"]*w-?2[^"]*)"', W2_ONLY),
    ]
    for pattern, bucket in patterns_value:
        if re.search(pattern, raw_html, re.I):
            return bucket
    # Badge-like text (e.g. in script or data attributes)
    if re.search(r'\bContract\s+Corp\s*[-]?\s*To\s*[-]?\s*Corp\b', raw_html, re.I):
        return C2C_ONLY
    if re.search(r'\bCORP_TO_CORP\b', raw_html):
        return C2C_ONLY
    if re.search(r'\bContract\s+W-?2\b', raw_html, re.I):
        return W2_ONLY
    return None


def classify_w2_c2c(title: str, description: str, full_page_text: str = "") -> Optional[str]:
    """
    Legacy: Classify W2 or C2C from title and description. Returns 'W2', 'C2C', or None.
    Uses classify_w2_c2c_bucket and maps bucket to legacy value.
    """
    bucket = classify_w2_c2c_bucket(title, description, full_page_text)
    return bucket_to_legacy(bucket)


def extract_is_remote_and_work_type(
    job_data: Optional[Dict[str, Any]], description: str = "", raw_html: str = ""
) -> Tuple[Optional[bool], Optional[str]]:
    """Returns (is_remote, work_from_home_type). work_from_home_type: 'Remote' | 'Hybrid' | 'On-site'."""
    is_remote = None
    work_type = None
    if job_data and isinstance(job_data, dict):
        # Direct flags
        if job_data.get("isRemote") is True or job_data.get("remote") is True:
            is_remote = True
            work_type = "Remote"
        for key in ("workPlaceType", "workplaceType", "workPlace", "employmentLocationType"):
            val = job_data.get(key)
            if val and isinstance(val, str):
                v = val.strip().lower()
                if "remote" in v or v == "remote":
                    is_remote = True
                    work_type = "Remote"
                    break
                if "hybrid" in v:
                    is_remote = False
                    work_type = "Hybrid"
                    break
                if "on-site" in v or "onsite" in v or "on_site" in v or "office" in v:
                    is_remote = False
                    work_type = "On-site"
                    break
    combined = f" {description} {raw_html} ".lower()
    if work_type is None:
        if re.search(r"\bremote\s+(?:only|position|job|work|role)\b", combined) or re.search(r"\bwork\s+from\s+home\b", combined) or "100% remote" in combined or "fully remote" in combined:
            is_remote = True
            work_type = "Remote"
        elif re.search(r"\bhybrid\s+(?:position|job|work|role|model)\b", combined) or "hybrid work" in combined or "hybrid role" in combined:
            is_remote = False
            work_type = "Hybrid"
        elif re.search(r"\bon-?site\b", combined) or "in-office" in combined:
            is_remote = False
            work_type = "On-site"
    if is_remote is None and work_type:
        is_remote = work_type == "Remote"
    return (is_remote, work_type)


def extract_company_url(job_data: Optional[Dict[str, Any]], raw_html: str = "") -> Optional[str]:
    if job_data and isinstance(job_data, dict):
        for key in ("company", "hiringOrganization"):
            org = job_data.get(key)
            if isinstance(org, dict):
                for url_key in ("url", "websiteUrl", "website", "homepage", "companyUrl"):
                    u = org.get(url_key)
                    if u and isinstance(u, str):
                        u = clean_url(u)
                        if u.startswith("http") and "dice.com" not in u.lower():
                            return u
        for key in ("companyUrl", "company_url", "employerUrl"):
            u = job_data.get(key)
            if u and isinstance(u, str):
                u = clean_url(u)
                if u.startswith("http") and "dice.com" not in u.lower():
                    return u
    if raw_html:
        for pattern in [r'"companyUrl"\s*:\s*"(https?://[^"]+)"', r'"websiteUrl"\s*:\s*"(https?://[^"]+)"', r'"url"\s*:\s*"(https?://[^"]+)"']:
            m = re.search(pattern, raw_html)
            if m:
                u = clean_url(m.group(1))
                if u.startswith("http") and "dice.com" not in u.lower():
                    return u
    return None


def extract_company_industry(job_data: Optional[Dict[str, Any]], raw_html: str = "") -> Optional[str]:
    if job_data and isinstance(job_data, dict):
        for key in ("industry", "industryName", "jobCategory", "category", "sector"):
            val = job_data.get(key)
            if val and isinstance(val, str) and len(val) < 200:
                return val.strip()
        org = job_data.get("company") or job_data.get("hiringOrganization")
        if isinstance(org, dict) and org.get("industry"):
            return str(org["industry"]).strip() if len(str(org["industry"])) < 200 else None
    if raw_html:
        m = re.search(r'"industry"\s*:\s*"([^"]+)"', raw_html)
        if m and len(m.group(1)) < 200:
            return m.group(1).strip()
    return None


def extract_company_description(job_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract company description/about from job data when present."""
    if not job_data or not isinstance(job_data, dict):
        return None
    for key in ("company", "hiringOrganization"):
        org = job_data.get(key)
        if isinstance(org, dict):
            for desc_key in ("description", "about", "aboutUs", "overview"):
                val = org.get(desc_key)
                if val and isinstance(val, str) and 50 < len(val) < 5000:
                    return val.strip()
    val = job_data.get("companyDescription") or job_data.get("employerDescription")
    if val and isinstance(val, str) and 50 < len(val) < 5000:
        return val.strip()
    return None


def extract_job_level(title: str = "", description: str = "") -> Optional[str]:
    """
    Infer job level from title/description and return LinkedIn-style seniority labels
    so that experience_level (job_level) is consistent with LinkedIn:
    Internship, Entry level, Associate, Mid-Senior level, Director, Executive.
    """
    combined = f" {title} {description} ".lower()
    # Executive (VP, C-level, Chief) - check before Director
    if re.search(r"\b(?:vp|vice\s+president|c-?level|chief|\bcxo\b|ceo|cto|cfo|coo)\b", combined):
        return "Executive"
    # Director / Head of
    if re.search(r"\bdirector\b", combined) or re.search(r"\bhead\s+of\b", combined):
        return "Director"
    # Mid-Senior level: Senior, Principal, Staff, Manager, Mid-level (same as LinkedIn)
    if (
        re.search(r"\bsenior\b", combined)
        or re.search(r"\bsr\.\b", combined)
        or re.search(r"\bprincipal\b", combined)
        or re.search(r"\blead\s+(?:engineer|developer)\b", combined)
        or re.search(r"\bstaff\b", combined)
        or re.search(r"\bmanager\b", combined)
        or re.search(r"\bmanagement\b", combined)
        or re.search(r"\bmid\s*level\b", combined)
        or re.search(r"\bmid-level\b", combined)
    ):
        return "Mid-Senior level"
    # Associate (LinkedIn uses this as distinct from Entry level)
    if re.search(r"\bassociate\b", combined):
        return "Associate"
    # Entry level: Junior, Entry level
    if re.search(r"\bjunior\b", combined) or re.search(r"\bjr\.\b", combined) or re.search(r"\bentry\s*level\b", combined):
        return "Entry level"
    # Internship
    if re.search(r"\bintern\b", combined) or re.search(r"\binternship\b", combined):
        return "Internship"
    return None


def extract_external_apply_url_fallback(soup: BeautifulSoup, job_data: Optional[Dict] = None) -> Optional[str]:
    if job_data:
        for field in ['applyUrl', 'externalApplyUrl', 'directApplyUrl', 'url']:
            u = job_data.get(field)
            if u and isinstance(u, str):
                u = clean_url(u)
                if u.startswith('http') and 'dice.com' not in u:
                    return u
    for selector in [{'data-testid': 'apply-button'}, {'data-testid': 'external-apply-button'}, {'data-testid': 'direct-apply-button'}]:
        btn = soup.find('a', attrs=selector)
        if btn and btn.get('href'):
            href = clean_url(btn.get('href'))
            if href.startswith('http') and 'dice.com' not in href:
                return href
    for script in soup.find_all('script'):
        text = script.string or ''
        for pattern in [r'applyUrl["\']?\s*:\s*["\'](https?://[^"\']+)["\']', r'externalApplyUrl["\']?\s*:\s*["\'](https?://[^"\']+)["\']']:
            m = re.search(pattern, text)
            if m:
                u = clean_url(m.group(1))
                if u.startswith('http') and 'dice.com' not in u:
                    return u
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if any(p in href.lower() for p in ['taleo', 'workday', 'greenhouse', 'lever', 'icims', 'myworkday', 'salesforce.wd12']):
            href = clean_url(href)
            if href.startswith('http'):
                return href
    return None