# 🔧 GitHub Actions Variables Explained

## 📋 **Key Variables in Our Workflows**

### **1. `secrets.GITHUB_TOKEN`**
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**What it is:**
- Automatically provided by GitHub Actions
- No setup required - GitHub creates it automatically
- Limited permissions to the current repository

**What it does:**
- Allows workflow to create GitHub releases
- Allows workflow to create comments on PRs/issues
- Allows workflow to update repository status

**Permissions:**
- ✅ Create releases
- ✅ Create comments
- ✅ Update repository status
- ❌ Access other repositories
- ❌ Access private repositories

### **2. `secrets.PYPI_API_TOKEN`**
```yaml
env:
  TWINE_USERNAME: __token__
  TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

**What it is:**
- Your PyPI API token (manually added)
- Required for publishing to PyPI

**Setup required:**
- Go to PyPI.org → Account Settings → API tokens
- Create token with "Entire account" scope
- Add to GitHub repository secrets

### **3. `github.ref`**
```yaml
if: startsWith(github.ref, 'refs/tags/')
```

**What it is:**
- Full Git reference that triggered the workflow
- Examples:
  - `refs/tags/v2.0.1` (tag push)
  - `refs/heads/main` (branch push)
  - `refs/pull/123/merge` (PR)

**Usage:**
- Check if workflow was triggered by tag
- Extract branch or tag information
- Conditional workflow steps

### **4. `github.ref_name`**
```yaml
tag_name: ${{ github.ref_name }}
```

**What it is:**
- Short name of the reference
- Examples:
  - `v2.0.1` (from `refs/tags/v2.0.1`)
  - `main` (from `refs/heads/main`)

**Usage:**
- Create releases with clean tag names
- Display branch names
- Use in release titles

## 🔍 **Variable Comparison**

| Variable | Full Reference | Short Name | Example |
|----------|---------------|------------|---------|
| `github.ref` | `refs/tags/v2.0.1` | `v2.0.1` | Full Git reference |
| `github.ref_name` | `v2.0.1` | `v2.0.1` | Short reference name |

## 📝 **Workflow Examples**

### **Tag-Based Publishing**
```yaml
# Triggered by: git push origin v2.0.1
on:
  push:
    tags:
      - 'v*'

# Variables available:
# github.ref = "refs/tags/v2.0.1"
# github.ref_name = "v2.0.1"
```

### **Branch-Based Testing**
```yaml
# Triggered by: git push origin main
on:
  push:
    branches: [ main ]

# Variables available:
# github.ref = "refs/heads/main"
# github.ref_name = "main"
```

### **Pull Request Testing**
```yaml
# Triggered by: PR to main branch
on:
  pull_request:
    branches: [ main ]

# Variables available:
# github.ref = "refs/pull/123/merge"
# github.ref_name = "123"
```

## 🚀 **Our Workflow Breakdown**

### **Publish Workflow (`publish.yml`)**
```yaml
# Triggered by tag push (e.g., v2.0.1)
on:
  push:
    tags:
      - 'v*'

# Variables used:
# - secrets.PYPI_API_TOKEN: Your PyPI token
# - secrets.GITHUB_TOKEN: Auto-provided by GitHub
# - github.ref: "refs/tags/v2.0.1"
# - github.ref_name: "v2.0.1"
```

**Steps:**
1. ✅ Checkout code
2. ✅ Set up Python
3. ✅ Install dependencies
4. ✅ Build package
5. ✅ Check package
6. ✅ Publish to PyPI (uses `secrets.PYPI_API_TOKEN`)
7. ✅ Create GitHub release (uses `secrets.GITHUB_TOKEN`)

### **Test Workflow (`test.yml`)**
```yaml
# Triggered by push/PR to main
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

# Variables used:
# - github.ref: "refs/heads/main" or "refs/pull/123/merge"
# - github.ref_name: "main" or "123"
```

**Steps:**
1. ✅ Checkout code
2. ✅ Set up Python (matrix: 3.10, 3.11, 3.12)
3. ✅ Install dependencies
4. ✅ Test imports
5. ✅ Test functionality

### **Build Workflow (`build.yml`)**
```yaml
# Triggered by push/PR to main
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

# Variables used:
# - github.ref: "refs/heads/main" or "refs/pull/123/merge"
```

**Steps:**
1. ✅ Checkout code
2. ✅ Set up Python
3. ✅ Install build dependencies
4. ✅ Check manifest
5. ✅ Build package
6. ✅ Validate package
7. ✅ Upload artifacts

## 🔧 **Setup Requirements**

### **Required Secrets**
1. **`PYPI_API_TOKEN`** (Manual setup required)
   - Go to PyPI.org → Account Settings → API tokens
   - Create token with "Entire account" scope
   - Add to GitHub repository secrets

2. **`GITHUB_TOKEN`** (Automatic)
   - Provided automatically by GitHub Actions
   - No setup required
   - Limited to current repository

### **Automatic Variables**
- `github.ref` - Full Git reference
- `github.ref_name` - Short reference name
- `github.sha` - Commit SHA
- `github.actor` - User who triggered the workflow
- `github.repository` - Repository name (e.g., "A6h9lash/jobspy-enhanced-scraper")

## 🎯 **Best Practices**

### **Security**
- ✅ Use `secrets.GITHUB_TOKEN` for GitHub operations
- ✅ Use `secrets.PYPI_API_TOKEN` for PyPI operations
- ✅ Never hardcode tokens in workflow files
- ✅ Use environment variables for sensitive data

### **Conditional Logic**
- ✅ Use `if: startsWith(github.ref, 'refs/tags/')` for tag-specific steps
- ✅ Use `if: github.ref == 'refs/heads/main'` for branch-specific steps
- ✅ Use `if: github.event_name == 'pull_request'` for PR-specific steps

### **Release Management**
- ✅ Use `github.ref_name` for clean tag names
- ✅ Use `github.ref` for full reference checks
- ✅ Use `secrets.GITHUB_TOKEN` for release creation

## 📊 **Variable Summary**

| Variable | Type | Setup | Purpose |
|----------|------|-------|---------|
| `secrets.GITHUB_TOKEN` | Secret | Automatic | GitHub operations |
| `secrets.PYPI_API_TOKEN` | Secret | Manual | PyPI publishing |
| `github.ref` | Context | Automatic | Full Git reference |
| `github.ref_name` | Context | Automatic | Short reference name |

**All variables are now properly configured in your workflows! 🚀**

