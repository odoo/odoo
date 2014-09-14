# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class account_invoice(models.Model):
    _inherit = ['account.invoice']
    
    sent_docsaway = fields.Boolean("Sent via DocsAway", default=False)
    date_sent_docsaway = fields.Datetime("Date Sent", default=False)

    @api.multi
    def invoice_send_letter(self):
        assert len(self.ids) == 1, 'This option should only be used for a single id at a time'
        recs = self.browse(self.ids)[0]
        return recs.env['mail_docsaway.api']._prepare_delivery(self.ids, 'account.invoice', 'account.report_invoice', recs.partner_id)

    @api.model
    def _set_as_sent(self, ids):
        """ Set the invoices with id in ids as sent """
        elements = self.browse(ids)
        for element in elements:
            element.sent = True
            element.sent_docsaway = True
            element.date_sent_docsaway = datetime.datetime.now()
            element.message_post(body=_("This invoice was sent by post (via DocsAway)"))
