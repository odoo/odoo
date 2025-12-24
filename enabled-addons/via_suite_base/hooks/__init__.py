# -*- coding: utf-8 -*-
"""
ViaSuite Base Hooks
===================

Installation and configuration hooks:
- post_init_hook: Main orchestrator for module initialization
- sentry_init: Initialize Sentry error tracking
- logger_config: Configure structured logging
- branding: Branding customization utilities
"""

from . import post_init_hook
from . import sentry_init
from . import logger_config
from . import branding