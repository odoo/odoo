# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for OpenERP
#   Copyright (C) 2014 Akretion (http://www.akretion.com).
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#   @author Guewen Baconnier
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import logging
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import FailedJobError, NoExternalId
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector_ecommerce.event import on_tracking_number_added
from .connector import get_environment
from .backend import prestashop
from .unit.backend_adapter import PrestaShopCRUDAdapter

_logger = logging.getLogger(__name__)

@prestashop
class PrestashopTrackingExport(ExportSynchronizer):
    _model_name = ['prestashop.sale.order']

    def _get_tracking(self):
        trackings = []
        for picking in self.binding.picking_ids:
            if picking.carrier_tracking_ref:
                trackings.append(picking.carrier_tracking_ref)
        return ';'.join(trackings) if trackings else None


    def run(self, binding_id):
        """ Export the tracking number of a picking to Magento """
        # verify the picking is done + magento id exists
        tracking_adapter = self.get_connector_unit_for_model(
            PrestaShopCRUDAdapter, '__not_exit_prestashop.order_carrier')

        self.binding = self.session.browse(self.model._name, binding_id)
        tracking = self._get_tracking()
        if tracking:
            prestashop_order_id = self.binder.to_backend(binding_id)
            filters = {
                'filter[id_order]': prestashop_order_id,
            }
            order_carrier_id = tracking_adapter.search(filters)
            if order_carrier_id:
                order_carrier_id = order_carrier_id[0]
                vals = tracking_adapter.read(order_carrier_id)
                vals['tracking_number'] = tracking
                tracking_adapter.write(order_carrier_id, vals)
                return "Tracking %s exported" % tracking
            else:
                raise orm.except_orm(
                    _('Prestashop Error'),
                    _('No carrier found on sale order'))
        else:
            return "No tracking to export"


@on_tracking_number_added
def delay_export_tracking_number(session, model_name, record_id):
    """
    Call a job to export the tracking number to a existing picking that
    must be in done state.
    """
    # browse on stock.picking because we cant read on stock.picking.out
    # buggy virtual models... Anyway the ID is the same
    picking = session.browse('stock.picking', record_id)
    if picking.sale_id and picking.sale_id.prestashop_bind_ids:
        for binding in picking.sale_id.prestashop_bind_ids:
            export_tracking_number.delay(
                session,
                binding._model._name,
                binding.id,
                priority=20)


@job
def export_tracking_number(session, model_name, record_id):
    """ Export the tracking number of a delivery order. """
    order = session.browse(model_name, record_id)
    backend_id = order.backend_id.id
    env = get_environment(session, model_name, backend_id)
    tracking_exporter = env.get_connector_unit(PrestashopTrackingExport)
    return tracking_exporter.run(record_id)
