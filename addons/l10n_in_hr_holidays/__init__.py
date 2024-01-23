# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def _generate_public_leaves(env):
    env['resource.calendar.leaves'].generate_public_leaves()
