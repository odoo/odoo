import secrets
import psycopg2
import json

from odoo import fields, models, api, Command, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, UserError
from odoo.modules.registry import Registry
from odoo.tools import SQL
from odoo.addons.pos_urban_piper import const

from .pos_urban_piper_request import UrbanPiperClient


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_payment_methods(self):
        """
        Override default payment methods to filter out delivery payment methods.
        """
        payment_methods = super()._default_payment_methods()
        return payment_methods.filtered(lambda pm: not pm.is_delivery_payment)

    def _default_urbanpiper_store_identifier(self):
        """
        Default unique Urban Piper POS ID.
        """
        return secrets.token_hex()

    def _default_urbanpiper_pricelist(self):
        return self.env['product.pricelist'].search([
            ('name', 'ilike', 'Urbanpiper'),
            ('currency_id', '=', self.env.company.currency_id.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    def _default_urbanpiper_fiscal_position(self):
        fiscal_position = self.env.ref('pos_urban_piper.pos_account_fiscal_position_urbanpiper', False)
        if fiscal_position and fiscal_position.sudo().company_id.id == self.env.company.id:
            return fiscal_position

    name = fields.Char(
        translate=True,
    )
    urbanpiper_store_identifier = fields.Char(
        string='Urban Piper POS ID',
        help='Pos ID from Urban Piper (Atlas)',
        default=_default_urbanpiper_store_identifier,
        copy=False,
    )
    urbanpiper_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Urban Piper Pricelist',
        help='Pricelist for Urban Piper sync menu.',
        default=_default_urbanpiper_pricelist,
    )
    urbanpiper_fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        check_company=True,
        string='Urban Piper Fiscal Position',
        help='Fiscal position for Urban Piper sync menu.',
        default=_default_urbanpiper_fiscal_position,
    )
    urbanpiper_payment_methods_ids = fields.Many2many(
        'pos.payment.method',
        'pos_config_urbanpiper_payment_method_ids_rel', 'config_id',
        string='Urban Piper Payment Methods',
        help='Payment methods for Urban Piper sync menu.'
    )
    urbanpiper_last_sync_date = fields.Datetime(string='Last Sync on', help='Last sync date for menu sync.')
    urbanpiper_webhook_url = fields.Char(
        string='Register Urbanpiper Webhook URL',
        help='Store webhook url (base url) for security.'
    )
    urbanpiper_delivery_provider_ids = fields.Many2many(
        'pos.delivery.provider',
        string='Delivery Providers',
        help='The delivery providers used for online delivery through UrbanPiper.',
    )

    _sql_constraints = [('urbanpiper_store_identifier_uniq',
                         'unique(urbanpiper_store_identifier)',
                         'Store ID must be unique for every pos configuration.')]

    def _init_column(self, column_name):
        if column_name != 'urbanpiper_store_identifier':
            return super()._init_column(column_name)
        # fetch void columns
        self.env.cr.execute(SQL("SELECT id FROM pos_config WHERE urbanpiper_store_identifier IS NULL"))
        pos_config_ids = self.env.cr.fetchall()
        if not pos_config_ids:
            return
        # update existing columns
        for pos_config_id in pos_config_ids:
            self.env.cr.execute(SQL(
                """
                UPDATE pos_config SET urbanpiper_store_identifier = %s WHERE id = %s;
                """,
                self._default_urbanpiper_store_identifier(),
                pos_config_id[0]
            ))

    @api.model_create_multi
    def create(self, vals_list):
        pos_configs = super().create(vals_list)
        for config in pos_configs:
            if config.module_pos_urban_piper:
                config._setup_journals_and_payment_methods()
                config._configure_fiscal_position_and_pricelist()
        return pos_configs

    def write(self, vals):
        res = super().write(vals)
        for config in self:
            if (config.module_pos_urban_piper or vals.get('module_pos_urban_piper')) and vals.get('urbanpiper_store_identifier'):
                if not config.urbanpiper_payment_methods_ids or vals.get('urbanpiper_delivery_provider_ids'):
                    config._setup_journals_and_payment_methods()
                config._configure_fiscal_position_and_pricelist()
        return res

    def _setup_journals_and_payment_methods(self):
        """
        Fetch or create payment methods and enable option fiscal taxes.
        """
        self.ensure_one()
        delivery_providers = self.urbanpiper_delivery_provider_ids
        for delivery_provider in delivery_providers:
            journal = self.env['account.journal'].sudo().search([
                ('code', '=', f"{delivery_provider.journal_code}{self.id}"),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not journal:
                journal = self.env['account.journal'].sudo().create({
                    'name': f"{delivery_provider.name} - {self.name}",
                    'code': f"{delivery_provider.journal_code}{self.id}",
                    'type': 'bank',
                    'company_id': self.company_id.id,
                })
            payment_method = self.env['pos.payment.method'].sudo().search([
                ('journal_id', '=', journal.id),
                ('is_delivery_payment', '=', True),
                ('delivery_provider_id', '=', delivery_provider.id),
            ], limit=1)
            if not payment_method:
                payment_method = self.env['pos.payment.method'].sudo().create({
                    'name': f"{delivery_provider.name} - {self.name}",
                    'journal_id': journal.id,
                    'company_id': self.company_id.id,
                    'is_delivery_payment': True,
                    'delivery_provider_id': delivery_provider.id
                })
            self.urbanpiper_payment_methods_ids |= payment_method

    def _configure_fiscal_position_and_pricelist(self):
        """
        Set taxes in fiscal position for urban piper.
        """
        self.ensure_one()
        fiscal_position = self.urbanpiper_fiscal_position_id or self.env.ref('pos_urban_piper.pos_account_fiscal_position_urbanpiper', False)
        if not fiscal_position or fiscal_position.sudo().company_id.id != self.company_id.id:
            fiscal_position = self.env['account.fiscal.position'].create({
                'name': 'UrbanPiper'
            })
        if self.module_pos_urban_piper:
            if not self.urbanpiper_fiscal_position_id:
                self.urbanpiper_fiscal_position_id = fiscal_position
            if not self.urbanpiper_pricelist_id:
                pricelist = self.env['product.pricelist'].search([
                    ('name', 'ilike', 'UrbanPiper'),
                    ('currency_id', '=', self.company_id.currency_id.id),
                    ('company_id', '=', self.company_id.id)
                ])
                if not pricelist:
                    pricelist = self.env['product.pricelist'].create({
                        'name': 'UrbanPiper',
                        'currency_id': self.company_id.currency_id.id,
                        'item_ids': [Command.create({
                            'compute_price': 'percentage',
                            'percent_price': -30,
                        })]
                    })
                self.urbanpiper_pricelist_id = pricelist.id
        self._add_line_to_fiscal_position(fiscal_position)

    def _add_line_to_fiscal_position(self, fiscal_position):
        # Outside of India, prices are tax-inclusive. So if users want tax-specific behavior,
        # they must manually add a tax line to the fiscal position.
        pass

    def prepare_taxes_data(self, pos_products):
        """
        Prepare taxes data for urban piper for sync menu.
        """
        return []

    def update_urbanpiper_item_data(self, item, product):
        """
        Override this method to update item data with product information. (as per requirements for different regions)
        """
        self.ensure_one()
        return item

    def update_store_status(self, status):
        """
        Activate and Deactivate store
        """
        up = UrbanPiperClient(self.with_context(provider_name=self.env.context.get('providerName')))
        up.configure_webhook()
        up.urbanpiper_store_status_update(status)

    def order_status_update(self, order_id, new_status, code=None):
        """
        Update order status from urban piper webhook
        """
        self.ensure_one()
        order = self.env['pos.order'].browse(order_id)
        if new_status == 'Food Ready' and order.state != 'paid':
            self._make_order_payment(order)
        up = UrbanPiperClient(self)
        is_success, message = False, ''
        if order.delivery_provider_id.technical_name in ['careem'] and new_status == 'Food Ready':
            is_success = True
        else:
            is_success, message = up.request_status_update(order.delivery_identifier, new_status, code)
        if is_success:
            order.write({
                'delivery_status': const.ORDER_STATUS_MAPPING[new_status][1],
            })
            if new_status == 'Cancelled':
                # Prevent loading cancelled orders in `getServerOrders` triggered by `_send_delivery_order_count`
                order.state = 'cancel'
        if new_status == 'Acknowledged':
            up.urbanpiper_order_reference_update(order)
        self._send_delivery_order_count(order_id)
        return {'is_success': is_success, 'message': message}

    def _make_order_payment(self, order):
        """
        Make payment for order of urban piper orders.
        """
        self.ensure_one()
        payment_method = self.urbanpiper_payment_methods_ids.filtered(lambda pm: pm.delivery_provider_id.id == order.delivery_provider_id.id)
        if not payment_method:
            payment_method = self.urbanpiper_payment_methods_ids[0]
        context_payment = {
            'active_ids': [order.id],
            'active_id': order.id
        }
        self.env['pos.make.payment'].with_context(context_payment).create({
            'amount': order.amount_total,
            'payment_method_id': payment_method.id,
        }).check()
        order._compute_prices()

    def _send_delivery_order_count(self, order_id=None):
        """
        Send delivery order count to pos ui
        """
        self.ensure_one()
        if self.current_session_id:
            self._notify('DELIVERY_ORDER_COUNT', order_id)

    def _store_action_update(self, data):
        """
        Send store status update to pos ui
        """
        self.ensure_one()
        if self.current_session_id:
            self._notify('STORE_ACTION', data)

    def get_delivery_data(self):
        """
        Fetch delivery order count and providers for pos ui
        """
        self.ensure_one()
        delivery_order_count = self._get_urbanpiper_order_count()
        delivery_providers = self._get_active_delivery_providers()
        total_new_order = sum(
            provider_data.get('awaiting', 0)
            for provider_data in delivery_order_count['urbanpiper'].values()
        )
        combined_data = {
            'delivery_order_count': delivery_order_count,
            'delivery_providers': delivery_providers,
            'total_new_order': total_new_order,
        }
        return combined_data

    def _get_total_tax_tag(self):
        self.ensure_one()
        return 'total_included'

    def _get_urbanpiper_order_count(self):
        """
        Updates order count whenever order status changes and when new order receives
        """
        self.ensure_one()
        if not self.current_session_id:
            return {}
        session_id = self.current_session_id.id
        order_statuses = ['placed', 'acknowledged', 'food_ready', 'dispatched', 'completed']
        order_count_data = {}
        for provider in self.urbanpiper_delivery_provider_ids:
            order_counts = {
                status: self.env['pos.order'].search_count([
                    ('delivery_status', '=', status),
                    ('delivery_provider_id', '=', provider.id),
                    ('session_id', '=', session_id),
                    ('state', '!=', 'cancel')
                ]) for status in order_statuses
            }
            order_count_data[provider.technical_name] = {
                'awaiting': order_counts['placed'],
                'preparing': order_counts['acknowledged'],
                'done': order_counts['food_ready'] + order_counts['dispatched'] + order_counts['completed']
            }
        return {'urbanpiper': order_count_data}

    def _get_active_delivery_providers(self):
        """
        Fetch delivery providers for pos ui
        """
        urbanpiper_providers = []
        for provider in self.urbanpiper_delivery_provider_ids or []:
            urbanpiper_providers.append({
                'code': provider.technical_name,
                'name': provider.name,
                'image': provider.image_128,
                'id': provider.id
            })
        return urbanpiper_providers

    def _urbanpiper_handle_response(self, response_json, raise_exception=False):
        """
        Handle response from urban piper
        """
        title, msg_type, message = _('Urban Piper'), 'danger', ''
        if response_json.get('errors'):
            title = list(response_json.get('errors').keys())[0]
            message = list(response_json.get('errors').values())[0]
        elif response_json.get('message'):
            message = response_json.get('message')
            if response_json.get('status') == 'success':
                msg_type = 'success'
                message = message.split('.')[0]
            elif response_json.get('status') == 'error':
                if raise_exception:
                    raise ValidationError(response_json['message'])
        if message:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'type': msg_type,
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},  # force a form reload
                }
            }
        
    def prepare_store_data(self, data):
        self.ensure_one()
        return data

    def _check_required_request_params(self, store_required=True):
        msg = ''
        user_name = self.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.urbanpiper_username', False)
        api_key = self.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.urbanpiper_apikey', False)
        if not user_name:
            msg += _('UrbanPiper Username is required.\n')
        if not api_key:
            msg += _('UrbanPiper API Key is required.\n')
        if not self.urbanpiper_store_identifier and store_required:
            msg += _('UrbanPiper Store ID is required.\n')
        if msg:
            raise UserError(msg)

    def log_xml(self, xml_string, func):
        self.env.flush_all()
        db_name = self.env.cr.dbname

        try:
            with Registry(db_name).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                IrLogging = env['ir.logging']
                IrLogging.sudo().create({'name': 'Urban piper error handler',
                            'type': 'server',
                            'dbname': db_name,
                            'level': 'DEBUG',
                            'message': xml_string,
                            'path': 'Urbanpiper',
                            'func': func,
                            'line': 1})
        except psycopg2.Error:
            pass

    def _reset_urbanpiper_product_linkages(self):
        """
        Reset product linkage to Urbanpiper and products become available
        for syncing again.
        """
        if linked_statuses := self.env['product.urban.piper.status'].search([
            ('config_id', 'in', self.ids),
            ('is_product_linked', '=', True)
        ]):
            linked_statuses.write({'is_product_linked': False})

    def get_urban_piper_provider_states(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.toggle_state') or "{}"
        config_state = json.loads(raw)
        config_state = config_state.get(str(self.id), {})
        return config_state

    def set_urban_piper_provider_states(self, value_json):
        config_state = json.loads(self.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.toggle_state', "{}"))
        config_state[str(self.id)] = json.loads(value_json or "{}")
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.toggle_state', json.dumps(config_state))
        self._notify('URBAN_PIPER_PROVIDER_STATES', config_state[str(self.id)])
        return config_state[str(self.id)]
