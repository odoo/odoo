# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class AccountUpdateLockDate(models.TransientModel):
    _name = 'account.lock.date'
    _description = 'Lock date for accounting'

    company_id = fields.Many2one(comodel_name='res.company', string="Company",
                                 required=True)
    sale_lock_date = fields.Date(string="Sales Lock Date", help='Prevents creating and modifying invoices up to the date.')
    purchase_lock_date = fields.Date(string="Purchase Lock date", help='Prevents creating and modifying bills up to the date.')
    hard_lock_date = fields.Date(string="Lock Everyone",
                                       help="No users, including Advisers, can edit accounts prior to and "
                                            "inclusive of this date. Use it for fiscal year locking for "
                                            "example.")
    @api.model
    def default_get(self, field_list):
        res = super(AccountUpdateLockDate, self).default_get(field_list)
        company = self.env.company
        res.update({
            'company_id': company.id,
            'sale_lock_date': company.sale_lock_date,
            'purchase_lock_date': company.purchase_lock_date,
            'hard_lock_date': company.hard_lock_date,
        })
        return res

    def _check_execute_allowed(self):
        self.ensure_one()
        has_adviser_group = self.env.user.has_group(
            'account.group_account_manager')
        if not (has_adviser_group or self.env.uid == SUPERUSER_ID):
            raise UserError(_("You are not allowed to execute this action."))

    def execute(self):
        self.ensure_one()
        self._check_execute_allowed()
        self.company_id.sudo().write({
            'sale_lock_date': self.sale_lock_date,
            'purchase_lock_date': self.purchase_lock_date,
            'hard_lock_date': self.hard_lock_date,
        })
