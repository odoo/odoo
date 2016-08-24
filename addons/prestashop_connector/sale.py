#-*- coding: utf-8 -*-
from prestapyt import PrestaShopWebServiceDict

from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.unit.synchronizer import (Exporter)
from .unit.backend_adapter import GenericAdapter

from openerp.addons.connector_ecommerce.unit.sale_order_onchange import (
    SaleOrderOnChange)
from .connector import get_environment
from backend import prestashop


@prestashop
class PrestaShopSaleOrderOnChange(SaleOrderOnChange):
    _model_name = 'prestashop.sale.order'


@prestashop
class SaleOrderStateAdapter(GenericAdapter):
    _model_name = 'prestashop.sale.order.state'
    _prestashop_model = 'order_states'


@prestashop
class SaleOrderAdapter(GenericAdapter):
    _model_name = 'prestashop.sale.order'
    _prestashop_model = 'orders'
    _export_node_name = 'order'

    def update_sale_state(self, prestashop_id, datas):
        api = self.connect()
        return api.add('order_histories', datas)

    def search(self, filters=None):
        result = super(SaleOrderAdapter, self).search(filters=filters)

        shop_ids = self.session.search('prestashop.shop', [
            ('backend_id', '=', self.backend_record.id)
        ])
        shops = self.session.browse('prestashop.shop', shop_ids)
        for shop in shops:
            if not shop.default_url:
                continue

            api = PrestaShopWebServiceDict(
                '%s/api' % shop.default_url, self.prestashop.webservice_key
            )
            result += api.search(self._prestashop_model, filters)
        return result

# @prestashop
# class OrderCarriers(GenericAdapter):
#     _model_name = '__not_exit_prestashop.order_carrier'
#     _prestashop_model = 'order_carriers'
#     _export_node_name = 'order_carrier'
 

@prestashop
class PaymentMethodAdapter(GenericAdapter):
    _model_name = 'payment.method'
    _prestashop_model = 'orders'
    _export_node_name = 'order'
    
    def search(self, filters=None):
        api = self.connect()
        res = api.get(self._prestashop_model, options=filters)
        methods = res[self._prestashop_model][self._export_node_name]
        if isinstance(methods, dict):
            return [methods]
        return methods

@prestashop
class SaleOrderLineAdapter(GenericAdapter):
    _model_name = 'prestashop.sale.order.line'
    _prestashop_model = 'order_details'


@prestashop
class SaleStateExport(Exporter):
    _model_name = ['prestashop.sale.order']

    def run(self, prestashop_id, state):
        datas = {
            'order_history': {
                'id_order': prestashop_id,
                'id_order_state': state,
            }
        }
        self.backend_adapter.update_sale_state(prestashop_id, datas)


# TODO improve me, don't try to export state if the sale order does not come
#      from a prestashop connector
# TODO improve me, make the search on the sale order backend only
@on_record_write(model_names='sale.order')
def prestashop_sale_state_modified(session, model_name, record_id,
                                   fields=None):
    if 'state' in fields:
        sale = session.browse(model_name, record_id)
        # a quick test to see if it is worth trying to export sale state
        states = session.search(
            'sale.order.state.list',
            [('name', '=', sale.state)]
        )
        if states:
            export_sale_state.delay(session, record_id, priority=20)
    return True


def find_prestashop_state(session, sale_state, backend_id):
    state_list_model = 'sale.order.state.list'
    state_list_ids = session.search(
        state_list_model,
        [('name', '=', sale_state)]
    )
    for state_list in session.browse(state_list_model, state_list_ids):
        if state_list.prestashop_state_id.backend_id.id == backend_id:
            return state_list.prestashop_state_id.prestashop_id
    return None


@job
def export_sale_state(session, record_id):
    inherit_model = 'prestashop.sale.order'
    sale_ids = session.search(inherit_model, [('openerp_id', '=', record_id)])
    if not isinstance(sale_ids, list):
        sale_ids = [sale_ids]
    for sale in session.browse(inherit_model, sale_ids):
        backend_id = sale.backend_id.id
        new_state = find_prestashop_state(session, sale.state, backend_id)
        if new_state is None:
            continue
        env = get_environment(session, inherit_model, backend_id)
        sale_exporter = env.get_connector_unit(SaleStateExport)
        sale_exporter.run(sale.prestashop_id, new_state)
