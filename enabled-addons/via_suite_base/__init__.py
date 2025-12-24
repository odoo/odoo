# -*- coding: utf-8 -*-
"""
ViaSuite Base Module
====================

Core module for ViaSuite retail solution.

This module provides base customizations including:
- Keycloak SSO integration
- S3 storage backend
- Amazon SES email
- Structured logging
- Sentry monitoring
- Custom branding
"""

from . import models
from . import hooks
from . import utils

from .hooks.post_init_hook import post_init_hook

__version__ = '19.0.1.0.0'