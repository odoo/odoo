# -*- coding: utf-8 -*-
from openerp.osv import fields, orm


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.res.partner', 'openerp_id',
            string="PrestaShop Bindings"
        ),
        'prestashop_address_bind_ids': fields.one2many(
            'prestashop.address', 'openerp_id',
            string="PrestaShop Address Bindings"
        ),
    }


class prestashop_res_partner(orm.Model):
    _name = 'prestashop.res.partner'
    _inherit = 'prestashop.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'shop_group_id'

    def _get_prest_partner_from_website(self, cr, uid, ids, context=None):
        prest_partner_obj = self.pool['prestashop.res.partner']
        return prest_partner_obj.search(
            cr,
            uid,
            [('shop_group_id', 'in', ids)],
            context=context
        )

    _columns = {
        'openerp_id': fields.many2one(
            'res.partner',
            string='Partner',
            required=True,
            ondelete='cascade'
        ),
        'backend_id': fields.related(
            'shop_group_id',
            'backend_id',
            type='many2one',
            relation='prestashop.backend',
            string='Prestashop Backend',
            store={
                'prestashop.res.partner': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['shop_group_id'],
                    10
                ),
                'prestashop.website': (
                    _get_prest_partner_from_website,
                    ['backend_id'],
                    20
                ),
            },
            readonly=True
        ),
        'shop_group_id': fields.many2one(
            'prestashop.shop.group',
            string='PrestaShop Shop Group',
            required=True,
            ondelete='restrict'
        ),
        'shop_id': fields.many2one(
            'prestashop.shop',
            string='PrestaShop Shop'
        ),
        'group_ids': fields.many2many(
            'prestashop.res.partner.category',
            'prestashop_category_partner',
            'partner_id',
            'category_id',
            string='PrestaShop Groups'
        ),
        'date_add': fields.datetime(
            'Created At (on PrestaShop)',
            readonly=True
        ),
        'date_upd': fields.datetime(
            'Updated At (on PrestaShop)',
            readonly=True
        ),
        'newsletter': fields.boolean('Newsletter'),
        'default_category_id': fields.many2one(
            'prestashop.res.partner.category',
            'PrestaShop default category',
            help="This field is synchronized with the field "
            "'Default customer group' in PrestaShop."
        ),
        'birthday': fields.date('Birthday'),
        'company': fields.char('Company'),
        'prestashop_address_bind_ids': fields.one2many(
            'prestashop.address', 'openerp_id',
            string="PrestaShop Address Bindings"
        ),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(shop_group_id, prestashop_id)',
         'A partner with the same ID on PrestaShop already exists for this '
         'website.'),
    ]


class prestashop_address(orm.Model):
    _name = 'prestashop.address'
    _inherit = 'prestashop.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'backend_id'

    def _get_prest_address_from_partner(self, cr, uid, ids, context=None):
        prest_address_obj = self.pool['prestashop.address']
        return prest_address_obj.search(
            cr,
            uid,
            [('prestashop_partner_id', 'in', ids)],
            context=context
        )

    _columns = {
        'openerp_id': fields.many2one(
            'res.partner',
            string='Partner',
            required=True,
            ondelete='cascade'
        ),
        'date_add': fields.datetime(
            'Created At (on Prestashop)',
            readonly=True
        ),
        'date_upd': fields.datetime(
            'Updated At (on Prestashop)',
            readonly=True
        ),
        'prestashop_partner_id': fields.many2one(
            'prestashop.res.partner',
            string='Prestashop Partner',
            required=True,
            ondelete='cascade'
        ),
        'backend_id': fields.related(
            'prestashop_partner_id',
            'backend_id',
            type='many2one',
            relation='prestashop.backend',
            string='Prestashop Backend',
            store={
                'prestashop.address': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['prestashop_partner_id'],
                    10
                ),
                'prestashop.res.partner': (
                    _get_prest_address_from_partner,
                    ['backend_id', 'shop_group_id'],
                    20
                ),
            },
            readonly=True
        ),
        'shop_group_id': fields.related(
            'prestashop_partner_id',
            'shop_group_id',
            type='many2one',
            relation='prestashop.shop.group',
            string='PrestaShop Shop Group',
            store={
                'prestashop.address': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['prestashop_partner_id'],
                    10
                ),
                'prestashop.res.partner': (
                    _get_prest_address_from_partner,
                    ['shop_group_id'],
                    20
                ),
            },
            readonly=True
        ),
        'vat_number': fields.char('PrestaShop VAT'),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A partner address with the same ID on PrestaShop already exists.'),
    ]


class res_partner_category(orm.Model):
    _inherit = 'res.partner.category'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.res.partner.category',
            'openerp_id',
            string='PrestaShop Bindings',
            readonly=True),
    }


class prestashop_res_partner_category(orm.Model):
    _name = 'prestashop.res.partner.category'
    _inherit = 'prestashop.binding'
    _inherits = {'res.partner.category': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'res.partner.category',
            string='Partner Category',
            required=True,
            ondelete='cascade'
        ),
        'date_add': fields.datetime(
            'Created At (on Prestashop)',
            readonly=True
        ),
        'date_upd': fields.datetime(
            'Updated At (on Prestashop)',
            readonly=True
        ),
        # TODO add prestashop shop when the field will be available in the api.
        # we have reported the bug for it
        # see http://forge.prestashop.com/browse/PSCFV-8284
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         'A partner group with the same ID on PrestaShop already exists.'),
    ]
