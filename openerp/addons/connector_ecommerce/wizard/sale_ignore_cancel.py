# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api


class SaleIgnoreCancel(models.TransientModel):
    _name = 'sale.ignore.cancel'
    _description = 'Ignore Sales Order Cancel'

    reason = fields.Html(required=True)

    @api.multi
    def confirm_ignore_cancel(self):
        self.ensure_one()
        sale_ids = self.env.context.get('active_ids')
        assert sale_ids
        sales = self.env['sale.order'].browse(sale_ids)
        sales.ignore_cancellation(self.reason)
        return {'type': 'ir.actions.act_window_close'}
