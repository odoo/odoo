# -*- coding: utf-8 -*-
##############################################################################
#
#    Authors: Guewen Baconnier, Sébastien Beau, David Béal
#    Copyright (C) 2010 BEAU Sébastien
#    Copyright 2011-2013 Camptocamp SA
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

import logging
from openerp.osv import fields, orm
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper,
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.mapper import PrestashopImportMapper
from .unit.import_synchronizer import (DelayedBatchImport,
                                       PrestashopImportSynchronizer,
                                       )
from .backend import prestashop

_logger = logging.getLogger(__name__)


@prestashop
class DeliveryCarrierAdapter(GenericAdapter):
    _model_name = 'prestashop.delivery.carrier'
    _prestashop_model = 'carriers'

    def search(self, filters=None):
        if filters is None:
            filters = {}
        filters['filter[deleted]'] = 0

        return super(DeliveryCarrierAdapter, self).search(filters)


@prestashop
class DeliveryCarrierImport(PrestashopImportSynchronizer):
    _model_name = ['prestashop.delivery.carrier']


@prestashop
class CarrierImportMapper(PrestashopImportMapper):
    _model_name = 'prestashop.delivery.carrier'
    direct = [
        ('name', 'name_ext'),
        ('name', 'name'),
        ('id_reference', 'id_reference'),
    ]

    @mapping
    def active(self, record):
        return {'active_ext': record['active'] == '1'}

    @mapping
    def product_id(self, record):
        if self.backend_record.shipping_product_id:
            return {'product_id': self.backend_record.shipping_product_id.id}
        prod_mod = self.session.pool['product.product']
        default_ship_product = prod_mod.search(
            self.session.cr,
            self.session.uid,
            [('default_code', '=', 'SHIP'),
             ('company_id', '=', self.backend_record.company_id.id)],
        )
        if default_ship_product:
            return {'product_id': default_ship_product[0]}
        return {}

    @mapping
    def partner_id(self, record):
        partner_pool = self.session.pool['res.partner']
        default_partner = partner_pool.search(
            self.session.cr,
            self.session.uid,
            [],
        )[0]
        return {'partner_id': default_partner}

    @mapping
    def prestashop_id(self, record):
        return {'prestashop_id': record['id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def company_id(self, record):
        return {'company_id': self.backend_record.company_id.id}


@prestashop
class DeliveryCarrierBatchImport(DelayedBatchImport):
    """ Import the Prestashop Carriers.
    """
    _model_name = ['prestashop.delivery.carrier']

    def run(self, filters=None, **kwargs):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search()
        _logger.info('search for prestashop carriers %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id, **kwargs)
