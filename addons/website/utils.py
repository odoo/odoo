# -*- coding: utf-8 -*-
import re

__all__ = ['slugify']

try:
    # use python-slugify (https://github.com/un33k/python-slugify) if available
    from slugify import slugify
except ImportError:
    def slugify(s, max_length=None):
        spaceless = re.sub(r'\s+', '-', s)
        specialless = re.sub(r'[^-_A-Za-z0-9]', '', spaceless)
        return specialless[:max_length]
