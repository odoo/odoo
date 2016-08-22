import logging
import pytz
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.session import ConnectorSession

from openerp import fields, models, api

_logger = logging.getLogger(__name__)


class prestashop_backend(models.Model):

    _name = 'prestashop_backend'
    _description = u'Prestashop Backend'

    def _select_versions(self,cr,uid,context=None):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return [('1.6', '1.6.0.9'),
            ('1.5', '1.5')
        ]

    version = fields.Selection(
        selection='_select_versions',
        string='Version',
        required=True,
    )
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Warehouse',
        required=True,
        help='Warehouse used to compute the stock quantities.'
    )
    
    import_partners_since= fields.Datetime('Import partners since')
    import_orders_since= fields.Datetime('Import Orders since')
    import_products_since= fields.Datetime('Import Products since')
    import_refunds_since= fields.Datetime('Import Refunds since')
    import_suppliers_since= fields.Datetime('Import Suppliers since')
    company_id= fields.Many2one('res.company', 'Company', select=1, required=True)
    discount_product_id= fields.Many2one('product.product', 'Dicount Product', select=1, required=False)
    shipping_product_id= fields.Many2one('product.product', 'Shipping Product', select=1, required=False)
    
    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'prestashop.backend', context=c),
    }
    
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

    def import_customers_since(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = self._date_as_user_tz(
                cr, uid, backend_record.import_partners_since
            )
            import_customers_since.delay(
                session,
                backend_record.id,
                since_date,
                priority=10,
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
            import_products.delay(session, backend_record.id, since_date, priority=10)
        return True

class prestashop_binding(models.AbstractModel):
    _name = 'prestashop.binding'
    _inherit = 'external.binding'
    _description = 'Prestashop Binding (abstract)'

    backend_id = fields.Many2one(
        comodel_name='prestashop.backend',
        string='Prestashop Backend',
        required=True,
        ondelete='restrict',
    )
    prestashop_id = fields.Char(string='ID in the Prestashop', select=True)