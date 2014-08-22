# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<https://www.odoo.com>).
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

from openerp import api, fields, models
from openerp.tools.translate import _
import datetime


class sale_order(models.Model):
    _inherit = ['sale.order']

    sent_docsaway = fields.Boolean("Sent via DocsAway", default=False)
    date_sent_docsaway = fields.Datetime("Date Sent", default=False)

    @api.multi
    def send_letter_quotation(self):
        assert len(self.ids) == 1, 'This option should only be used for a single id at a time'
        recs = self.browse(self.ids)
        return recs.env['print.docsaway']._prepare_delivery(self.ids, 'sale.order', 'sale.report_saleorder', recs.partner_id)

    @api.model
    def _set_as_sent(self, ids):
        """ Set the sale orders with id in ids as sent """
        elements = self.browse(ids)
        for element in elements:
            element.sent_docsaway = True
            element.date_sent_docsaway = datetime.datetime.now()
            element.message_post(body=_("This sale order was sent by post (via DocsAway)"))
            element.signal_workflow('quotation_sent')
