# 🚀 GitHub Actions Workflows Guide

## 📁 **Workflow Files Created**

### **1. `.github/workflows/publish.yml` - PyPI Publishing**
- **Triggers**: 
  - Push tags (e.g., `v2.0.1`)
  - Manual workflow dispatch
- **Purpose**: Automatically publish package to PyPI when tags are pushed
- **Features**:
  - Builds package using `python -m build`
  - Checks package with `twine check`
  - Publishes to PyPI using API token
  - Creates GitHub release automatically

### **2. `.github/workflows/test.yml` - Package Testing**
- **Triggers**: 
  - Push to main/develop branches
  - Pull requests to main
  - Manual workflow dispatch
- **Purpose**: Test package compatibility across Python versions
- **Features**:
  - Tests on Python 3.10, 3.11, 3.12
  - Tests package installation
  - Tests all scraper imports
  - Tests model imports

### **3. `.github/workflows/build.yml` - Build Verification**
- **Triggers**: 
  - Push to main branch
  - Pull requests to main
  - Manual workflow dispatch
- **Purpose**: Verify package builds correctly
- **Features**:
  - Checks manifest file
  - Builds package
  - Validates package with twine
  - Tests installation from built wheel

## 🔧 **Setup Instructions**

### **Step 1: Configure PyPI API Token**

1. Go to [PyPI.org](https://pypi.org) and login
2. Go to Account Settings → API tokens
3. Create a new API token with scope "Entire account"
4. Copy the token (starts with `pypi-`)

### **Step 2: Add Secret to GitHub Repository**

1. Go to your GitHub repository
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Name: `PYPI_API_TOKEN`
5. Value: Your PyPI API token
6. Click "Add secret"

### **Step 3: Test the Workflows**

#### **Test Build Workflow:**
```bash
# Push to main branch to trigger build workflow
git add .
git commit -m "Add GitHub Actions workflows"
git push origin main
```

#### **Test Publishing Workflow:**
```bash
# Create and push a tag to trigger publishing
git tag v2.0.1
git push origin v2.0.1
```

## 📋 **Workflow Details**

### **Publishing Workflow (`publish.yml`)**

```yaml
# Triggers on tag push (e.g., v2.0.1)
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:  # Manual trigger
```

**Steps:**
1. ✅ Checkout code
2. ✅ Set up Python 3.10
3. ✅ Install build dependencies
4. ✅ Build package (`python -m build`)
5. ✅ Check package (`twine check`)
6. ✅ Publish to PyPI (`twine upload`)
7. ✅ Create GitHub release

### **Testing Workflow (`test.yml`)**

```yaml
# Triggers on push/PR to main
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
```

**Matrix Strategy:**
- Python 3.10
- Python 3.11  
- Python 3.12

**Test Steps:**
1. ✅ Checkout code
2. ✅ Set up Python (matrix)
3. ✅ Install dependencies
4. ✅ Install package in dev mode
5. ✅ Test basic import
6. ✅ Test scraper imports
7. ✅ Test model imports

### **Build Workflow (`build.yml`)**

```yaml
# Triggers on push/PR to main
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

**Build Steps:**
1. ✅ Checkout code
2. ✅ Set up Python 3.10
3. ✅ Install build dependencies
4. ✅ Check manifest file
5. ✅ Build package
6. ✅ Validate package
7. ✅ Upload build artifacts
8. ✅ Test installation from wheel

## 🚀 **Publishing Process**

### **Automatic Publishing (Recommended)**

1. **Update version numbers:**
   ```bash
   # Update pyproject.toml
   version = "2.0.1"
   
   # Update setup.py
   version="2.0.1"
   ```

2. **Commit and tag:**
   ```bash
   git add .
   git commit -m "Release v2.0.1"
   git tag v2.0.1
   git push origin main --tags
   ```

3. **GitHub Actions will automatically:**
   - Build the package
   - Publish to PyPI
   - Create GitHub release

### **Manual Publishing**

1. Go to GitHub repository
2. Click "Actions" tab
3. Select "Publish to PyPI" workflow
4. Click "Run workflow"
5. Enter version number
6. Click "Run workflow"

## 🔍 **Monitoring Workflows**

### **View Workflow Status**
1. Go to GitHub repository
2. Click "Actions" tab
3. View workflow runs and their status

### **Workflow Status Indicators**
- ✅ **Green**: Workflow completed successfully
- ❌ **Red**: Workflow failed
- 🟡 **Yellow**: Workflow in progress
- ⚪ **Gray**: Workflow not triggered

### **Common Issues and Solutions**

#### **Build Fails**
- Check `MANIFEST.in` file
- Verify all required files are included
- Check Python version compatibility

#### **Publishing Fails**
- Verify `PYPI_API_TOKEN` secret is set
- Check PyPI token permissions
- Ensure version number is unique

#### **Tests Fail**
- Check import statements
- Verify dependencies are correct
- Check Python version compatibility

## 📊 **Workflow Benefits**

### **Automation Benefits**
- ✅ **No manual publishing**: Tag push triggers automatic release
- ✅ **Multi-version testing**: Tests on Python 3.10, 3.11, 3.12
- ✅ **Build verification**: Ensures package builds correctly
- ✅ **Quality assurance**: Catches issues before publishing

### **Developer Benefits**
- ✅ **Easy releases**: Just push a tag
- ✅ **Automatic testing**: Tests run on every push/PR
- ✅ **Build validation**: Ensures package integrity
- ✅ **Documentation**: Automatic GitHub releases

### **User Benefits**
- ✅ **Reliable releases**: Tested on multiple Python versions
- ✅ **Quick updates**: Automated publishing process
- ✅ **Quality packages**: Built and validated automatically

## 🎯 **Best Practices**

### **Version Management**
- ✅ Use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Update version in both `pyproject.toml` and `setup.py`
- ✅ Tag releases with `v` prefix (e.g., `v2.0.1`)

### **Testing**
- ✅ Test locally before pushing
- ✅ Use feature branches for development
- ✅ Create pull requests for code review

### **Publishing**
- ✅ Test build workflow before publishing
- ✅ Use pre-release versions for testing
- ✅ Document breaking changes in releases

**Your GitHub Actions workflows are now ready! 🚀**

The workflows will automatically:
- Test your package on multiple Python versions
- Build and validate your package
- Publish to PyPI when you push tags
- Create GitHub releases automatically
