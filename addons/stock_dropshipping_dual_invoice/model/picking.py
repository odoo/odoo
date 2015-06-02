#    Author: Leonardo Pistone
#    Copyright 2015 Camptocamp SA
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
from openerp import models, api


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _get_partner_to_invoice(self, picking):
        if 'partner_to_invoice_id' in self.env.context:
            return self.env.context['partner_to_invoice_id']
        else:
            return super(Picking, self)._get_partner_to_invoice(picking)
