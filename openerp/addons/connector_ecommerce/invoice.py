# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
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

from openerp import models, api
from openerp.addons.connector.session import ConnectorSession
from .event import on_invoice_paid, on_invoice_validated


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def confirm_paid(self):
        res = super(AccountInvoice, self).confirm_paid()
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        for record_id in self.ids:
            on_invoice_paid.fire(session, self._name, record_id)
        return res

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        for record_id in self.ids:
            on_invoice_validated.fire(session, self._name, record_id)
        return res
