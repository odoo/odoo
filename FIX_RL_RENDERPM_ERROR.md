# Fixing rl-renderPM Installation Error

## The Problem

When installing Odoo requirements on Windows, you get this error:
```
ERROR: Failed to build 'rl-renderPM' when getting requirements to build wheel
ImportError: cannot import name 'get_abi_tag' from 'wheel.bdist_wheel'
```

## Why This Happens

`rl-renderPM` is a Windows-specific package that:
- Has build issues with newer Python versions
- Requires compilation from source
- Is only needed for advanced reportlab features (renderPM)
- **Is optional** for basic Odoo functionality

## Solution: Skip rl-renderPM

### Method 1: Install Without rl-renderPM (Recommended)

```powershell
# Create a filtered requirements file
$content = Get-Content requirements.txt
$filtered = $content | Where-Object { $_ -notmatch '^rl-renderPM' }
$filtered | Out-File -FilePath requirements_temp.txt -Encoding utf8

# Install from filtered file
pip install -r requirements_temp.txt

# Clean up
Remove-Item requirements_temp.txt
```

### Method 2: Install Everything Except rl-renderPM

```powershell
pip install -r requirements.txt --ignore-installed rl-renderPM
```

However, this may still try to build it. Better to use Method 1.

### Method 3: Install Manually Without rl-renderPM

If you need all packages except rl-renderPM, you can install them individually or use:

```powershell
pip install -r requirements.txt 2>&1 | Out-Null
# Then install missing packages manually if needed
```

## Is rl-renderPM Required?

**No!** `rl-renderPM` is optional. It's only needed if you:
- Use reportlab's renderPM features
- Need advanced PDF rendering with PM (PixMap) support

For standard Odoo functionality, you don't need it.

## Verify Installation

After installing, verify Odoo works:

```powershell
python odoo-bin --version
```

If this works, you're good to go!

## Alternative: Use Pre-built Wheels

If you really need rl-renderPM later, you can try:
1. Installing Visual C++ Build Tools
2. Or finding pre-built wheels for your Python version
3. Or using a different Python version that has wheels available

But for Odoo, you typically don't need it.
