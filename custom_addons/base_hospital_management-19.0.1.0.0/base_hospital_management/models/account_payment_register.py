# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Subina P (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    """
    Adding inpatient field to invoicing model.
    """
    _inherit = "account.payment.register"

    @api.model
    def create(self, vals_list):
        """Create records to inpatient payment"""
        for vals in vals_list:
            self.env['inpatient.payment'].sudo().create({
                'name': vals['communication'],
                'subtotal': vals['amount'],
                'inpatient_id': self.env['hospital.inpatient'].sudo().search([(
                    'patient_id', '=', vals['partner_id'])],
                    order='create_date desc', limit=1).id,
                'date': vals['payment_date']
            })
        return super().create(vals_list)
