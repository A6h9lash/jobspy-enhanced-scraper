#!/bin/bash
# Simple build script for linkedin-jobspy package

set -e

echo "Building linkedin-jobspy package..."

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build the package
python -m build

echo "Build completed!"
echo "Files created:"
ls -la dist/

echo ""
echo "To upload to PyPI:"
echo "1. Test PyPI: python -m twine upload --repository testpypi dist/*"
echo "2. Real PyPI: python -m twine upload dist/*"
