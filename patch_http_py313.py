#!/usr/bin/env python3
"""
Patch Odoo 18.0 http.py for Python 3.13 compatibility.
Fixes NameError: name 'GEOIP_EMPTY_COUNTRY' is not defined
"""

import sys

def patch_http_file():
    filepath = r"C:\Users\lided\projects\odoo\odoo\http.py"
    
    print(f"Patching {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The problematic code
    old_code = """    def __getattr__(self, attr):
        # Be smart and determine whether the attribute exists on the
        # country object or on the city object.
        if hasattr(GEOIP_EMPTY_COUNTRY, attr):
            return getattr(self._country_record, attr)
        if hasattr(GEOIP_EMPTY_CITY, attr):
            return getattr(self._city_record, attr)
        raise AttributeError(f"{self} has no attribute {attr!r}")"""
    
    # Fixed code with try/except for NameError
    new_code = """    def __getattr__(self, attr):
        # Be smart and determine whether the attribute exists on the
        # country object or on the city object.
        try:
            if hasattr(GEOIP_EMPTY_COUNTRY, attr):
                return getattr(self._country_record, attr)
            if hasattr(GEOIP_EMPTY_CITY, attr):
                return getattr(self._city_record, attr)
        except NameError:
            pass
        raise AttributeError(f"{self} has no attribute {attr!r}")"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Successfully patched http.py for Python 3.13 compatibility!")
        print("  - Added try/except NameError handler in __getattr__ method")
        return True
    else:
        print("✗ Could not find the expected code pattern.")
        print("  File may already be patched or has a different structure.")
        return False

if __name__ == '__main__':
    success = patch_http_file()
    sys.exit(0 if success else 1)
