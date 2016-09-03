# -*- coding: utf-8 -*-

import logging
import pytz
from datetime import datetime

from openerp.osv import fields, orm
from openerp import api, models

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.session import ConnectorSession
from ...unit.import_synchronizer import (
    import_batch,
    import_customers_since,
    import_orders_since,
    import_products,
    import_refunds,
    import_product_attribute,
    import_suppliers,
    import_record,
    export_product_quantities,
)
from ...unit.direct_binder import DirectBinder
from ...connector import get_environment

# from ..product import import_inventory

_logger = logging.getLogger(__name__)


class prestashop_backend(orm.Model):
    _name = 'prestashop.backend'
    _doc = 'Prestashop Backend'
    _inherit = 'connector.backend'

    _backend_type = 'prestashop'

    def _select_versions(self, cr, uid, context=None):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return [('1.6', 'Version 1.6')]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'location': fields.char('Location'),
        'webservice_key': fields.char(
            'Webservice key',
            help="You have to put it in 'username' of the PrestaShop "
                 "Webservice api path invite"
        ),
        'warehouse_id': fields.many2one(
            'stock.warehouse',
            'Warehouse',
            required=True,
            help='Warehouse used to compute the stock quantities.'
        ),
        'taxes_included': fields.boolean("Use tax included prices"),
        'import_partners_since': fields.datetime('Import partners since'),
        'import_orders_since': fields.datetime('Import Orders since'),
        'import_products_since': fields.datetime('Import Products since'),
        'import_refunds_since': fields.datetime('Import Refunds since'),
        'import_suppliers_since': fields.datetime('Import Suppliers since'),
        'language_ids': fields.one2many(
            'prestashop.res.lang',
            'backend_id',
            'Languages'
        ),
        'company_id': fields.many2one('res.company', 'Company', select=1, required=True),
        'discount_product_id': fields.many2one('product.product', 'Dicount Product', select=1, required=False),
        'shipping_product_id': fields.many2one('product.product', 'Shipping Product', select=1, required=False),
        'property_account_receivable_id': fields.many2one('account.account', 'Account Receivable', select=1, required=True),
        'property_account_payable_id': fields.many2one('account.account', 'Account Payable', select=1, required=True),
        'unrealized_product_category_id': fields.many2one('product.category', 'Unrealized Product Category', select=1, required=True),
        'tax_out_id': fields.many2one('account.tax', 'Tax Out', select=1, required=True),
    }

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'prestashop.backend', context=c),
    }

    def synchronize_metadata(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            for model in ('prestashop.shop.group',
                          'prestashop.shop',):
                import_batch(session, model, backend_id)
            
        return True

    def synchronize_basedata(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            for model_name in [
                'prestashop.res.lang',
            ]:
                env = get_environment(session, model_name, backend_id)
                directBinder = env.get_connector_unit(DirectBinder)
                directBinder.run()

            import_product_attribute(session, 'prestashop.product.attribute', backend_id)
            import_batch(session, 'prestashop.product.attribute.value', backend_id, None)
            #import_batch(session, 'prestashop.sale.order.state', backend_id)
        return True

    def _date_as_user_tz(self, cr, uid, dtstr):
        if not dtstr:
            return None
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, uid)
        timezone = pytz.timezone(user.partner_id.tz or 'utc')
        dt = datetime.strptime(dtstr, DEFAULT_SERVER_DATETIME_FORMAT)
        dt = pytz.utc.localize(dt)
        dt = dt.astimezone(timezone)
        return dt
    
    def import_product_attribute(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            import_product_attribute(
                session,
                'prestashop.product.attribute',
                backend_record.id,
            )

        return True

    def import_customers_since(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = self._date_as_user_tz(
                cr, uid, backend_record.import_partners_since
            )
            import_customers_since(
                session,
                'prestashop.res.partner',
                backend_record.id,
                since_date,
            )

        return True

    def import_products(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = self._date_as_user_tz(
                cr, uid, backend_record.import_products_since
            )
            import_products(session, 'prestashop.product.template', backend_record.id, since_date)
        return True

    def update_product_stock_qty(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        export_product_quantities.delay(session, ids)
        return True

    def import_stock_qty(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        # for backend_id in ids:
        #     import_inventory.delay(session, backend_id)

    def import_sale_orders(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = self._date_as_user_tz(
                cr, uid, backend_record.import_orders_since
            )
            import_orders_since.delay(
                session,
                backend_record.id,
                since_date,
                priority=5,
            )
        return True

    def import_payment_methods(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            import_batch.delay(session, 'payment.method', backend_record.id)
        return True

    def import_refunds(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = self._date_as_user_tz(
                cr, uid, backend_record.import_refunds_since
            )
            import_refunds.delay(session, backend_record.id, since_date)
        return True

    def _scheduler_launch(self, cr, uid, callback, domain=None,
                          context=None):
        if domain is None:
            domain = []
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

    def _scheduler_update_product_stock_qty(self, cr, uid, domain=None,
                                            context=None):
        self._scheduler_launch(cr, uid, self.update_product_stock_qty,
                               domain=domain, context=context)

    def _scheduler_import_sale_orders(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_sale_orders, domain=domain,
                               context=context)

    def _scheduler_import_customers(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_customers_since,
                               domain=domain, context=context)

    def _scheduler_import_products(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_products, domain=domain,
                               context=context)

    def _scheduler_import_payment_methods(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_payment_methods,
                               domain=domain, context=context)

    def _scheduler_import_refunds(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_refunds,
                               domain=domain, context=context)

    def _scheduler_import_suppliers(self, cr, uid, domain=None, context=None):
        self._scheduler_launch(cr, uid, self.import_suppliers,
                               domain=domain, context=context)

    def import_record(self, cr, uid, backend_id, model_name, ext_id,
                      context=None):
        session = ConnectorSession(cr, uid, context=context)
        import_record(session, model_name, backend_id, ext_id)
        return True


class prestashop_binding(orm.AbstractModel):
    _name = 'prestashop.binding'
    _inherit = 'external.binding'
    _description = 'PrestaShop Binding (abstract)'

    _columns = {
        # 'openerp_id': openerp-side id must be declared in concrete model
        'backend_id': fields.many2one(
            'prestashop.backend',
            'PrestaShop Backend',
            required=True,
            ondelete='restrict'),
        # TODO : do I keep the char like in Magento, or do I put a PrestaShop ?
        'prestashop_id': fields.integer('ID on PrestaShop'),
    }

    # the _sql_contraints cannot be there due to this bug:
    # https://bugs.launchpad.net/openobject-server/+bug/1151703

    def resync(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        func = import_record
        if context and context.get('connector_delay'):
            func = import_record.delay
        for product in self.browse(cr, uid, ids, context=context):
            func(
                session,
                self._name,
                product.backend_id.id,
                product.prestashop_id
            )
        return True


# TODO remove external.shop.group from connector_ecommerce
class prestashop_shop_group(orm.Model):
    _name = 'prestashop.shop.group'
    _inherit = 'prestashop.binding'
    _description = 'PrestaShop Shop Group'

    _columns = {
        'name': fields.char('Name', required=True),
        'shop_ids': fields.one2many(
            'prestashop.shop',
            'shop_group_id',
            string="Shops",
            readonly=True),
        'company_id': fields.related('backend_id', 'company_id', type="many2one", relation="res.company",string='Company', store=False),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A shop group with the same ID on PrestaShop already exists.'),
    ]


# TODO migrate from sale.shop
class prestashop_shop(orm.Model):
    _name = 'prestashop.shop'
    _inherit = 'prestashop.binding'
    _description = 'PrestaShop Shop'

    _inherits = {'sale.shop': 'openerp_id'}

    def _get_shop_from_shopgroup(self, cr, uid, ids, context=None):
        return self.pool.get('prestashop.shop').search(
            cr,
            uid,
            [('shop_group_id', 'in', ids)],
            context=context
        )

    _columns = {
        'shop_group_id': fields.many2one(
            'prestashop.shop.group',
            'PrestaShop Shop Group',
            required=True,
            ondelete='cascade'
        ),
        'openerp_id': fields.many2one(
            'sale.shop',
            string='Sale Shop',
            required=True,
            readonly=True,
            ondelete='cascade'
        ),
        # what is the exact purpose of this field?
        'default_category_id': fields.many2one(
            'product.category',
            'Default Product Category',
            help="The category set on products when?? TODO."
            "\nOpenERP requires a main category on products for accounting."
        ),
        'backend_id': fields.related(
            'shop_group_id',
            'backend_id',
            type='many2one',
            relation='prestashop.backend',
            string='PrestaShop Backend',
            store={
                'prestashop.shop': (
                    lambda self, cr, uid, ids, c={}: ids,
                    ['shop_group_id'],
                    10
                ),
                'prestashop.shop.group': (
                    _get_shop_from_shopgroup,
                    ['backend_id'],
                    20
                ),
            },
            readonly=True
        ),
        'default_url': fields.char('Default url'),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A shop with the same ID on PrestaShop already exists.'),
    ]


class sale_shop(orm.Model):
    _inherit = 'sale.shop'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.shop', 'openerp_id',
            string='PrestaShop Bindings',
            readonly=True),
        'company_id': fields.many2one('res.company', 'Company', select=1, required=True),
        'warehouse_id': fields.many2one(
            'stock.warehouse',
            'Warehouse',
            required=True,
            help='Warehouse used to compute the stock quantities.'
        ),
    }


class prestashop_res_lang(orm.Model):
    _name = 'prestashop.res.lang'
    _inherit = 'prestashop.binding'
    _inherits = {'res.lang': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'res.lang',
            string='Lang',
            required=True,
            ondelete='cascade'
        ),
        'active': fields.boolean('Active in prestashop'),
    }

    _defaults = {
        #'active': lambda *a: False,
        'active': False,
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A Lang with the same ID on Prestashop already exists.'),
    ]


class res_lang(orm.Model):
    _inherit = 'res.lang'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.res.lang',
            'openerp_id',
            string='prestashop Bindings',
            readonly=True),
    }


class prestashop_res_country(orm.Model):
    _name = 'prestashop.res.country'
    _inherit = 'prestashop.binding'
    _inherits = {'res.country': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'res.country',
            string='Country',
            required=True,
            ondelete='cascade'
        ),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A Country with the same ID on prestashop already exists.'),
    ]


class res_country(orm.Model):
    _inherit = 'res.country'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.res.country',
            'openerp_id',
            string='prestashop Bindings',
            readonly=True
        ),
    }


class prestashop_res_currency(orm.Model):
    _name = 'prestashop.res.currency'
    _inherit = 'prestashop.binding'
    _inherits = {'res.currency': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'res.currency',
            string='Currency',
            required=True,
            ondelete='cascade'
        ),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A Currency with the same ID on prestashop already exists.'),
    ]


class res_currency(orm.Model):
    _inherit = 'res.currency'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.res.currency',
            'openerp_id',
            string='prestashop Bindings',
            readonly=True
        ),
    }


class prestashop_account_tax(orm.Model):
    _name = 'prestashop.account.tax'
    _inherit = 'prestashop.binding'
    _inherits = {'account.tax': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'account.tax',
            string='Tax',
            required=True,
            ondelete='cascade'
        ),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A Tax with the same ID on prestashop already exists.'),
    ]


class account_tax(orm.Model):
    _inherit = 'account.tax'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.account.tax',
            'openerp_id',
            string='prestashop Bindings',
            readonly=True
        ),
    }


class prestashop_account_tax_group(orm.Model):
    _name = 'prestashop.account.tax.group'
    _inherit = 'prestashop.binding'
    _inherits = {'account.tax.group': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'account.tax.group',
            string='Tax Group',
            required=True,
            ondelete='cascade'
        ),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A Tax Group with the same ID on prestashop already exists.'),
    ]


class account_tax_group(orm.Model):
    _inherit = 'account.tax.group'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.account.tax.group',
            'openerp_id',
            string='Prestashop Bindings',
            readonly=True
        ),
        'company_id': fields.many2one('res.company', 'Company', select=1, required=True),
    }

class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.model
    def assign_then_enqueue(self, cr, uid, context=None):
        """"""
        session = ConnectorSession(cr, uid, context=context)
        