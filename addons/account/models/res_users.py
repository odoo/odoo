# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class Users(models.Model):
    _inherit = "res.users"

    @api.multi
    @api.constrains('groups_id')
    def _check_one_user_type(self):
        super(Users, self)._check_one_user_type()
        for user in self:
            if (user.user_has_groups('account.group_show_line_subtotals_tax_included') and
                    user.user_has_groups('account.group_show_line_subtotals_tax_excluded')):
                raise ValidationError(_('A user cannot have both Tax B2B and Tax B2C'))
