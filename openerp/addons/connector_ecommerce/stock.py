# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
#    Copyright 2013-2015 Camptocamp SA
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

from openerp.addons.connector.session import ConnectorSession
from .event import on_picking_out_done, on_tracking_number_added


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    related_backorder_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='backorder_id',
        string="Related backorders",
    )

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if vals.get('carrier_tracking_ref'):
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=self.env.context)
            for record_id in self.ids:
                on_tracking_number_added.fire(session, self._name, record_id)
        return res

    @api.multi
    def do_transfer(self):
        # The key in the context avoid the event to be fired in
        # StockMove.action_done(). Allow to handle the partial pickings
        self_context = self.with_context(__no_on_event_out_done=True)
        result = super(StockPicking, self_context).do_transfer()
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        for picking in self:
            if picking.picking_type_id.code != 'outgoing':
                continue
            if picking.related_backorder_ids:
                method = 'partial'
            else:
                method = 'complete'
            on_picking_out_done.fire(session, 'stock.picking',
                                     picking.id, method)

        return result


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        fire_event = not self.env.context.get('__no_on_event_out_done')
        if fire_event:
            pickings = self.mapped('picking_id')
            states = {p.id: p.state for p in pickings}

        result = super(StockMove, self).action_done()

        if fire_event:
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=self.env.context)
            for picking in pickings:
                if states[picking.id] != 'done' and picking.state == 'done':
                    if picking.picking_type_id.code != 'outgoing':
                        continue
                    # partial pickings are handled in
                    # StockPicking.do_transfer()
                    on_picking_out_done.fire(session, 'stock.picking',
                                             picking.id, 'complete')

        return result
