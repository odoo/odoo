# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _


class pos_config(osv.osv):
    _name = 'pos.config'

    POS_CONFIG_STATE = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated')
    ]

    def _get_currency(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, False)
        for pos_config in self.browse(cr, uid, ids, context=context):
            if pos_config.journal_id:
                currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
            else:
                currency_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id.id
            result[pos_config.id] = currency_id
        return result

    def _get_current_session(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict()

        for record in self.browse(cr, uid, ids, context=context):
            session_id = record.session_ids.filtered(lambda r: r.user_id.id == uid and not r.state == 'closed')
            result[record.id] = {
                'current_session_id': session_id,
                'current_session_state': session_id.state,
            }
        return result

    def _get_last_session(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict()

        for record in self.browse(cr, uid, ids, context=context):
            session_ids = self.pool['pos.session'].search_read(
                cr, uid,
                [('config_id', '=', record.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at'],
                order="stop_at desc", limit=1, context=context)
            if session_ids:
                result[record.id] = {
                    'last_session_closing_cash': session_ids[0]['cash_register_balance_end_real'],
                    'last_session_closing_date': session_ids[0]['stop_at'],
                }
            else:
                result[record.id] = {
                    'last_session_closing_cash': 0,
                    'last_session_closing_date': None,
                }
        return result

    def _get_current_session_user(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict()

        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = record.session_ids.filtered(lambda r: r.state == 'opened').user_id.name
        return result

    _columns = {
        'name' : fields.char('Point of Sale Name', select=1,
             required=True, help="An internal identification of the point of sale"),
        'journal_ids' : fields.many2many('account.journal', 'pos_config_journal_rel', 
             'pos_config_id', 'journal_id', 'Available Payment Methods',
             domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type'),
        'stock_location_id': fields.many2one('stock.location', 'Stock Location', domain=[('usage', '=', 'internal')], required=True),
        'journal_id' : fields.many2one('account.journal', 'Sale Journal',
             domain=[('type', '=', 'sale')],
             help="Accounting journal used to post sales entries."),
        'currency_id' : fields.function(_get_currency, type="many2one", string="Currency", relation="res.currency"),
        'iface_cashdrawer' : fields.boolean('Cashdrawer', help="Automatically open the cashdrawer"),
        'iface_payment_terminal' : fields.boolean('Payment Terminal', help="Enables Payment Terminal integration"),
        'iface_electronic_scale' : fields.boolean('Electronic Scale', help="Enables Electronic Scale integration"),
        'iface_vkeyboard' : fields.boolean('Virtual KeyBoard', help="Enables an integrated Virtual Keyboard"),
        'iface_print_via_proxy' : fields.boolean('Print via Proxy', help="Bypass browser printing and prints via the hardware proxy"),
        'iface_scan_via_proxy' : fields.boolean('Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner"),
        'iface_invoicing': fields.boolean('Invoicing',help='Enables invoice generation from the Point of Sale'),
        'iface_big_scrollbars': fields.boolean('Large Scrollbars',help='For imprecise industrial touchscreens'),
        'iface_fullscreen':     fields.boolean('Fullscreen', help='Display the Point of Sale in full screen mode'),
        'iface_print_auto': fields.boolean('Automatic Receipt Printing', help='The receipt will automatically be printed at the end of each order'),
        'iface_print_skip_screen': fields.boolean('Skip Receipt Screen', help='The receipt screen will be skipped if the receipt can be printed automatically.'),
        'iface_precompute_cash': fields.boolean('Prefill Cash Payment',  help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount'),
        'iface_tax_included':   fields.boolean('Include Taxes in Prices', help='The displayed prices will always include all taxes, even if the taxes have been setup differently'),
        'iface_start_categ_id': fields.many2one('pos.category','Start Category', help='The point of sale will display this product category by default. If no category is specified, all available products will be shown'),
        'iface_display_categ_images': fields.boolean('Display Category Pictures', help="The product categories will be displayed with pictures."),
        'receipt_header': fields.text('Receipt Header',help="A short text that will be inserted as a header in the printed receipt"),
        'receipt_footer': fields.text('Receipt Footer',help="A short text that will be inserted as a footer in the printed receipt"),
        'proxy_ip':       fields.char('IP Address', help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty', size=45),

        'state' : fields.selection(POS_CONFIG_STATE, 'Status', required=True, readonly=True, copy=False),
        'uuid'  : fields.char('uuid', readonly=True, help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data'),
        'sequence_id' : fields.many2one('ir.sequence', 'Order IDs Sequence', readonly=True,
            help="This sequence is automatically created by Odoo but you can change it "\
                "to customize the reference numbers of your orders.", copy=False),
        'session_ids': fields.one2many('pos.session', 'config_id', 'Sessions'),
        'current_session_id': fields.function(_get_current_session, multi="session", type="many2one", relation="pos.session", string="Current Session"),
        'current_session_state': fields.function(_get_current_session, multi="session", type='char'),
        'last_session_closing_cash': fields.function(_get_last_session, multi="last_session", type='float'),
        'last_session_closing_date': fields.function(_get_last_session, multi="last_session", type='date'),
        'pos_session_username': fields.function(_get_current_session_user, type='char'),
        'group_by' : fields.boolean('Group Journal Items', help="Check this if you want to group the Journal Items by Product while closing a Session"),
        'pricelist_id': fields.many2one('product.pricelist','Pricelist', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'barcode_nomenclature_id':  fields.many2one('barcode.nomenclature','Barcodes', help='Defines what kind of barcodes are available and how they are assigned to products, customers and cashiers', required=True),
        'group_pos_manager_id': fields.many2one('res.groups','Point of Sale Manager Group', help='This field is there to pass the id of the pos manager group to the point of sale client'),
        'group_pos_user_id':    fields.many2one('res.groups','Point of Sale User Group', help='This field is there to pass the id of the pos user group to the point of sale client'),
        'tip_product_id':       fields.many2one('product.product','Tip Product', help="The product used to encode the customer tip. Leave empty if you do not accept tips."),
    }

    def _check_company_location(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.stock_location_id.company_id and config.stock_location_id.company_id.id != config.company_id.id:
                return False
        return True

    def _check_company_journal(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.journal_id and config.journal_id.company_id.id != config.company_id.id:
                return False
        return True

    def _check_company_payment(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            journal_ids = [j.id for j in config.journal_ids]
            if self.pool['account.journal'].search(cr, uid, [
                    ('id', 'in', journal_ids),
                    ('company_id', '!=', config.company_id.id)
                ], count=True, context=context):
                return False
        return True

    _constraints = [
        (_check_company_location, "The company of the stock location is different than the one of point of sale", ['company_id', 'stock_location_id']),
        (_check_company_journal, "The company of the sale journal is different than the one of point of sale", ['company_id', 'journal_id']),
        (_check_company_payment, "The company of a payment method is different than the one of point of sale", ['company_id', 'journal_ids']),
    ]

    def name_get(self, cr, uid, ids, context=None):
        result = []
        states = {
            'opening_control': _('Opening Control'),
            'opened': _('In Progress'),
            'closing_control': _('Closing Control'),
            'closed': _('Closed & Posted'),
        }
        for record in self.browse(cr, uid, ids, context=context):
            if (not record.session_ids) or (record.session_ids[0].state=='closed'):
                result.append((record.id, record.name+' ('+_('not used')+')'))
                continue
            session = record.session_ids[0]
            result.append((record.id, record.name + ' ('+session.user_id.name+')')) #, '+states[session.state]+')'))
        return result

    def _default_sale_journal(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale'), ('company_id', '=', company_id)], limit=1, context=context)
        return res and res[0] or False

    def _default_pricelist(self, cr, uid, context=None):
        res = self.pool.get('product.pricelist').search(cr, uid, [], limit=1, context=context)
        return res and res[0] or False

    def _get_default_location(self, cr, uid, context=None):
        wh_obj = self.pool.get('stock.warehouse')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = wh_obj.search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        if res and res[0]:
            return wh_obj.browse(cr, uid, res[0], context=context).lot_stock_id.id
        return False

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        print company_id
        return company_id

    def _get_default_nomenclature(self, cr, uid, context=None):
        nom_obj = self.pool.get('barcode.nomenclature')
        res = nom_obj.search(cr, uid, [], limit=1, context=context)
        return res and res[0] or False

    def _get_group_pos_manager(self, cr, uid, context=None):
        group = self.pool.get('ir.model.data').get_object_reference(cr,uid,'point_of_sale','group_pos_manager')
        if group:
            return group[1]
        else:
            return False

    def _get_group_pos_user(self, cr, uid, context=None):
        group = self.pool.get('ir.model.data').get_object_reference(cr,uid,'point_of_sale','group_pos_user')
        if group:
            return group[1]
        else:
            return False

    _defaults = {
        'uuid'  : lambda self, cr, uid, context={}: str(uuid.uuid4()),
        'state' : POS_CONFIG_STATE[0][0],
        'journal_id': _default_sale_journal,
        'group_by' : True,
        'pricelist_id': _default_pricelist,
        'iface_invoicing': True,
        'iface_print_auto': True,
        'iface_print_skip_screen': True,
        'stock_location_id': _get_default_location,
        'company_id': _get_default_company,
        'barcode_nomenclature_id': _get_default_nomenclature,
        'group_pos_manager_id': _get_group_pos_manager,
        'group_pos_user_id': _get_group_pos_user,
    }

    def onchange_picking_type_id(self, cr, uid, ids, picking_type_id, context=None):
        p_type_obj = self.pool.get("stock.picking.type")
        p_type = p_type_obj.browse(cr, uid, picking_type_id, context=context)
        if p_type.default_location_src_id and p_type.default_location_src_id.usage == 'internal' and p_type.default_location_dest_id and p_type.default_location_dest_id.usage == 'customer':
            return {'value': {'stock_location_id': p_type.default_location_src_id.id}}
        return False

    def set_active(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'active'}, context=context)

    def set_inactive(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'inactive'}, context=context)

    def set_deprecate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'deprecated'}, context=context)

    def create(self, cr, uid, values, context=None):
        ir_sequence = self.pool.get('ir.sequence')
        # force sequence_id field to new pos.order sequence
        values['sequence_id'] = ir_sequence.create(cr, SUPERUSER_ID, {
            'name': 'POS Order %s' % values['name'],
            'padding': 4,
            'prefix': "%s/"  % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }, context=context)

        # TODO master: add field sequence_line_id on model
        # this make sure we always have one available per company
        ir_sequence.create(cr, SUPERUSER_ID, {
            'name': 'POS order line %s' % values['name'],
            'padding': 4,
            'prefix': "%s/"  % values['name'],
            'code': "pos.order.line",
            'company_id': values.get('company_id', False),
        }, context=context)

        return super(pos_config, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.sequence_id:
                obj.sequence_id.unlink()
        return super(pos_config, self).unlink(cr, uid, ids, context=context)

    # Methods to open the POS

    def open_ui(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "you can open only one session at a time"

        record = self.browse(cr, uid, ids[0], context=context)
        context = dict(context or {})
        context['active_id'] = record.current_session_id.id
        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    def open_existing_session_cb_close(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "you can open only one session at a time"

        record = self.browse(cr, uid, ids[0], context=context)
        record.current_session_id.signal_workflow('cashbox_control')
        return self.open_session_cb(cr, uid, ids, context)

    def open_session_cb(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "you can open only one session at a time"

        proxy = self.pool.get('pos.session')
        record = self.browse(cr, uid, ids[0], context=context)
        current_session_id = record.current_session_id
        if not current_session_id:
            values = {
                'user_id': uid,
                'config_id': record.id,
            }
            session_id = proxy.create(cr, uid, values, context=context)
            record.current_session_id = proxy.browse(cr, uid, session_id, context=context)
            if record.current_session_id.state == 'opened':
                return self.open_ui(cr, uid, ids, context=context)
            return self._open_session(session_id)
        return self._open_session(current_session_id.id)

    def open_existing_session_cb(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "you can open only one session at a time"

        record = self.browse(cr, uid, ids[0], context=context)
        return self._open_session(record.current_session_id.id)

    def _open_session(self, session_id):
        return {
            'name': _('Session'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }