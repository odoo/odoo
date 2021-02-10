# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Users(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_username = fields.Char("Livechat Username", help="This username will be used as your name in the livechat channels.")
    # Discuss category livechat open status
    is_category_livechat_open = fields.Boolean("Is category livechat open", default=True)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on livechat_username
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['livechat_username'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['livechat_username'])
        return init_res

    def get_category_open_states(self):
        """ Override of get_categories_open_status to add livechat category
        """
        states = super(Users, self).get_category_open_states()
        states['is_category_livechat_open'] = self.is_category_livechat_open
        return states

    def set_category_open_states(self, category_id, is_open):
        """ Override of set_category_open_states to add livechat category
        """
        self.ensure_one()
        if category_id == 'livechat':
            self.sudo().write({'is_category_livechat_open': is_open})
            data = self.get_category_open_states()
            data['type'] = 'category_states'
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.partner_id.id), data)
        else:
            return super(Users, self).set_category_open_states(category_id, is_open)
