# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PortalGroup(models.Model):
    """ A portal is simply a group of users with the flag 'is_portal' set to True.
        The flag 'is_portal' makes a user group usable as a portal.
    """

    _inherit = 'res.groups'
