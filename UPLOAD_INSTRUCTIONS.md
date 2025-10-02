# LinkedIn JobSpy - Upload to PyPI Instructions

## Package Successfully Built! 🎉

Your `linkedin-jobspy` package has been successfully built and is ready for upload to PyPI.

**Built files:**
- `dist/linkedin_jobspy-1.0.0-py3-none-any.whl` (wheel)
- `dist/linkedin_jobspy-1.0.0.tar.gz` (source distribution)

## Next Steps to Upload to PyPI

### 1. Create PyPI Accounts

#### TestPyPI (for testing - recommended first):
- Go to: https://test.pypi.org/account/register/
- Create an account and verify your email

#### PyPI (for production):
- Go to: https://pypi.org/account/register/
- Create an account and verify your email

### 2. Generate API Tokens

#### For TestPyPI:
1. Log in to https://test.pypi.org/
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. Set scope to "Entire account" 
5. Copy the token (starts with `pypi-`)

#### For PyPI:
1. Log in to https://pypi.org/
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. Set scope to "Entire account"
5. Copy the token (starts with `pypi-`)

### 3. Upload Commands

#### Option A: Interactive Upload (you'll be prompted for credentials)

**Upload to TestPyPI first:**
```bash
cd /Users/nagabhaskar/development/jobspy-enhanced-scraper/linkedin-jobspy
source ../build-env/bin/activate
python -m twine upload --repository testpypi dist/*
```

**When prompted:**
- Username: `__token__`
- Password: [paste your TestPyPI API token]

**Upload to PyPI:**
```bash
python -m twine upload dist/*
```

**When prompted:**
- Username: `__token__`
- Password: [paste your PyPI API token]

#### Option B: Using .pypirc file (more secure)

Create `~/.pypirc` file:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-actual-pypi-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-actual-testpypi-token-here
```

Then upload:
```bash
# To TestPyPI
python -m twine upload --repository testpypi dist/*

# To PyPI
python -m twine upload dist/*
```

### 4. Verify Upload

#### TestPyPI:
- Check: https://test.pypi.org/project/linkedin-jobspy/
- Test install: `pip install --index-url https://test.pypi.org/simple/ linkedin-jobspy`

#### PyPI:
- Check: https://pypi.org/project/linkedin-jobspy/
- Test install: `pip install linkedin-jobspy`

### 5. Quick Upload Script

You can use this script for future uploads:

```bash
#!/bin/bash
cd /Users/nagabhaskar/development/jobspy-enhanced-scraper/linkedin-jobspy
source ../build-env/bin/activate

echo "Building package..."
rm -rf dist/ build/
python -m build

echo "Checking package..."
python -m twine check dist/*

echo "Uploading to TestPyPI..."
python -m twine upload --repository testpypi dist/*

echo "Upload to PyPI? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Uploading to PyPI..."
    python -m twine upload dist/*
    echo "✅ Package uploaded to PyPI!"
    echo "Install with: pip install linkedin-jobspy"
fi
```

## Package Information

- **Package Name:** `linkedin-jobspy`
- **Version:** `1.0.0`
- **Author:** Abhilash RS
- **License:** MIT
- **Python Support:** 3.10+

## Installation After Upload

Once uploaded to PyPI, users can install with:
```bash
pip install linkedin-jobspy
```

## Usage Example

```python
from linkedin_jobspy import LinkedIn, ScraperInput, Site, Country

scraper = LinkedIn()
search_params = ScraperInput(
    site_type=[Site.LINKEDIN],
    search_term="Data Scientist",
    location="San Francisco, CA",
    country=Country.USA,
    results_wanted=50
)

jobs = scraper.scrape(search_params)
print(f"Found {len(jobs.jobs)} jobs!")
```

## Support

After upload, your package will be available at:
- **PyPI:** https://pypi.org/project/linkedin-jobspy/
- **Install:** `pip install linkedin-jobspy`
- **Documentation:** Package README will be displayed on PyPI

## Troubleshooting

- **Authentication Error:** Check API tokens are correct
- **Package Name Exists:** Choose a different name if needed
- **Upload Fails:** Verify package integrity with `twine check dist/*`
- **Import Issues:** Ensure all dependencies are properly listed

Your package is ready! Just complete the PyPI account setup and upload! 🚀
