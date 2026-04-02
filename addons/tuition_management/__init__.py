# -*- coding: utf-8 -*-
from . import models


def _create_default_enquiry_stages(env):
    """Create default enquiry stages only if they don't exist. Called on install."""
    Stage = env['enquiry.stage']
    defaults = [
        ('New', 10, False, False),
        ('Demo Scheduled', 20, False, False),
        ('Enrolled', 40, False, True),
        ('Lost', 50, True, False),
    ]
    for name, sequence, fold, is_won in defaults:
        if not Stage.search([('name', '=', name)], limit=1):
            Stage.create({'name': name, 'sequence': sequence, 'fold': fold, 'is_won': is_won})
