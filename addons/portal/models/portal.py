# -*- coding: utf-8 -*-

from openerp import fields, models


class Portal(models.Model):
    """ A portal is simply a group of users with the flag 'is_portal' set to True.
        The flag 'is_portal' makes a user group usable as a portal.
    """
    _inherit = 'res.groups'

    is_portal = fields.Boolean(string='Portal', help="If checked, this group is usable as a portal.")
