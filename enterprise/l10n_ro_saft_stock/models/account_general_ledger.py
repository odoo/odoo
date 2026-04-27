from collections import defaultdict

from odoo import api, models
from odoo.tools import float_round
from odoo.exceptions import RedirectWarning
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import UOM_TO_UNECE_CODE


def safe_division(numerator, denominator):
    if not numerator or not denominator:
        return 0
    return numerator / denominator


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        # EXTENDS l10n_ro_saft
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'RO':
            return

        options['buttons'].append({
            'name': self.env._("SAF-T (D406 Stocks Declaration)"),
            'sequence': 52,
            'action': 'export_file',
            'action_param': 'l10n_ro_export_saft_to_xml_stocks',
            'file_export_type': self.env._("XML")
        })

    @api.model
    def l10n_ro_export_saft_to_xml_stocks(self, options):
        options['l10n_ro_saft_type'] = 'stocks'
        options['l10n_ro_saft_required_sections'] = self._set_l10n_ro_saft_stock_required_sections()
        return self.l10n_ro_export_saft_to_xml(options)

    @api.model
    def _set_l10n_ro_saft_stock_required_sections(self):
        return {
            'master_files': {
                'general_ledger_accounts': True,
                'customers': False,
                'suppliers': False,
                'tax_table': True,
                'uom_table': True,
                'analysis_type_table': True,
                'movement_type_table': True,
                'products': True,
                'physical_stocks': True,
                'owners': True,
                'assets': False,
            },
            'general_ledger_entries': False,
            'source_documents': {
                'sales_invoices': False,
                'purchase_invoices': False,
                'payments': False,
                'movement_of_goods': True,
                'asset_transactions': False,
            }
        }

    @api.model
    def _saft_prepare_report_initial_values(self, options, values):
        # EXTENDS account_saft
        # It runs the methods that fill l10n_ro_saft_stock_encountered_values before
        # the rest of the methods because the encountered values are used in the other
        # saft methods (e.g., encountered accounts are used in _saft_fill_report_general_ledger_accounts)
        super()._saft_prepare_report_initial_values(options, values)
        if options.get('l10n_ro_saft_type') == 'stocks':
            # the dict l10n_ro_saft_stock_encountered_values is used to collect
            # encountered l10n_ro_saft_stock relevant values. It also signals
            # that we are in a stock XML export
            values['l10n_ro_saft_stock_encountered_values'] = defaultdict(set)
            self._l10n_ro_saft_stock_fill_physical_stocks_values(options, values)
            self._l10n_ro_saft_stock_fill_movement_of_goods_values(options, values)
            self._l10n_ro_saft_stock_fill_movement_types_values(options, values)
            self._l10n_ro_saft_stock_fill_owners_values(options, values)

    @api.model
    def _l10n_ro_saft_fill_header_values(self, options, values):
        # EXTENDS l10n_ro_saft
        super()._l10n_ro_saft_fill_header_values(options, values)
        if values['company'].country_code == 'RO' and options.get('l10n_ro_saft_type') == 'stocks':
            values['declaration_type'] = 'C'

    @api.model
    def _saft_fill_report_general_ledger_accounts(self, report, options, values):
        # EXTENDS account_saft
        super()._saft_fill_report_general_ledger_accounts(report, options, values)

        if encountered_account_ids := values.get('l10n_ro_saft_stock_encountered_values', {}).get('account.account'):
            existing_account_ids = {vals['account'].id for vals in values['account_vals_list']}
            encountered_account_ids -= existing_account_ids
            encountered_accounts = self.env['account.account'].browse(encountered_account_ids)
            account_types_dict = dict(self.env['account.account']._fields['account_type']._description_selection(self.env))
            for account in encountered_accounts:
                values['account_vals_list'].append({
                    'account': account,
                    'account_type': account_types_dict[account.account_type],
                    'saft_account_type': self._saft_get_account_type(account.account_type),
                    'opening_balance': 0,
                    'closing_balance': 0,
                })

    def _get_encountered_product_uom_ids(self, values):
        # EXTENDS l10n_ro_saft
        result = super()._get_encountered_product_uom_ids(values)
        if 'l10n_ro_saft_stock_encountered_values' in values:
            result |= values['l10n_ro_saft_stock_encountered_values']['uom.uom']
        return result

    def _get_encountered_product_ids(self, values):
        # EXTENDS l10n_ro_saft
        result = super()._get_encountered_product_ids(values)
        if 'l10n_ro_saft_stock_encountered_values' in values:
            result |= values['l10n_ro_saft_stock_encountered_values']['product.product']
        return result

    def _validate_product_categories_accounts(self, categories):
        if not self.env.user.has_group('stock_account.group_stock_accounting_automatic'):
            raise RedirectWarning(
                self.env._("Automatic accounting must be enabled, and Stock Valuation Account must be set."),
                self.env.ref('account.action_account_config').id,
                self.env._("View Settings"),
            )

        if invalid_categories := categories.filtered(lambda c: not c.property_stock_valuation_account_id):
            raise RedirectWarning(
                self.env._("Each product category must have a Stock Valuation Account assigned."),
                invalid_categories._get_records_action(),
                self.env._("View Invalid Categories"),
            )

    @api.model
    def _l10n_ro_saft_stock_fill_physical_stocks_values(self, options, values):
        if not options['l10n_ro_saft_required_sections']['master_files']['physical_stocks']:
            return

        values['physical_stocks'] = []
        self.env['stock.quant']._quant_tasks()

        encountered_partner_ids = values['l10n_ro_saft_stock_encountered_values']['res.partner']
        encountered_account_ids = values['l10n_ro_saft_stock_encountered_values']['account.account']
        encountered_owner_account_codes = values['l10n_ro_saft_stock_encountered_values']['owner_account_codes']

        quantities_dict = defaultdict(lambda: {'before': 0, 'after': 0})
        domains = {
            'before': [('date', '<', options['date']['date_from'])],
            'after': [('date', '>=', options['date']['date_from']), ('date', '<=', options['date']['date_to'])],
        }
        for quantities_key, domain in domains.items():
            lines = self.env['stock.move.line']._read_group(
                domain=[
                    ('company_id', '=', values['company'].id),
                    ('state', '=', 'done'),
                    '|',
                    ('location_id.usage', 'in', ('internal', 'transit')),
                    ('location_dest_id.usage', 'in', ('internal', 'transit')),
                    *domain,
                ],
                aggregates=['quantity_product_uom:sum'],
                groupby=['product_id', 'location_id', 'location_dest_id', 'lot_id', 'owner_id'],
            )

            for product_id, location_id, location_dest_id, lot_id, owner_id, qty in lines:
                if location_id.usage in ('internal', 'transit'):
                    quantities_dict[product_id, location_id, lot_id, owner_id][quantities_key] -= qty
                if location_dest_id.usage in ('internal', 'transit'):
                    quantities_dict[product_id, location_dest_id, lot_id, owner_id][quantities_key] += qty

        for (product_id, location_id, lot_id, owner_id), qty in sorted(quantities_dict.items(), key=lambda kv: tuple(r.id for r in kv[0])):
            quantity_from = qty['before']
            quantity_to = qty['after'] + qty['before']
            if not quantity_from and not quantity_to:
                continue

            value_from = quantity_from * product_id.with_context(to_date=options['date']['date_from']).avg_cost
            value_to = quantity_to * product_id.with_context(to_date=options['date']['date_to']).avg_cost
            owner_id = owner_id or values['company'].partner_id

            values['physical_stocks'].append({
                'warehouse_id': location_id.warehouse_id.id,
                'location_id': location_id.id,
                'product_code': product_id.default_code or product_id.code,
                'lot': lot_id.name,
                'product_type': product_id.type,
                'commodity_code': self._get_commodity_code(product_id),
                'owner_id': self._l10n_ro_saft_get_registration_number(owner_id),
                'uom_physical_stock': UOM_TO_UNECE_CODE.get(product_id.uom_id.get_external_id()[product_id.uom_id.id], 'C62'),
                'uom_conversion_factor': 1,  # stock.quant is always in the product UOM
                'unit_price': float_round(product_id.standard_price or 0.0, 2),
                'opening_stock_quantity': float_round(quantity_from, 2),
                'opening_stock_value': float_round(value_from, 2),
                'closing_stock_quantity': float_round(quantity_to, 2),
                'closing_stock_value': float_round(value_to, 2),
                'stock_characteristic': product_id.name,
            })
            encountered_partner_ids.add(owner_id.id)
            encountered_account_ids.add(product_id.categ_id.property_stock_valuation_account_id.id)
            encountered_owner_account_codes.add((owner_id.id, product_id.categ_id.property_stock_valuation_account_id.code))

    @api.model
    def _l10n_ro_saft_stock_fill_movement_of_goods_values(self, options, values):
        if not options['l10n_ro_saft_required_sections']['source_documents']['movement_of_goods']:
            return

        values['movement_of_goods'] = {}
        values['movement_of_goods']['stock_movements'] = []
        values['movement_of_goods']['nb_stock_movement_lines'] = 0
        values['movement_of_goods']['total_quantity_received'] = 0
        values['movement_of_goods']['total_quantity_issued'] = 0

        moves = self.env['stock.move'].search([
            ('company_id', '=', values['company'].id),
            ('state', '=', 'done'),
            ('date', '>=', options['date']['date_from']),
            ('date', '<=', options['date']['date_to']),
        ])

        self._validate_product_categories_accounts(moves.move_line_ids.product_id.categ_id)

        encountered_picking_type_ids = values['l10n_ro_saft_stock_encountered_values']['stock.picking.type']
        encountered_uom_ids = values['l10n_ro_saft_stock_encountered_values']['uom.uom']
        encountered_product_ids = values['l10n_ro_saft_stock_encountered_values']['product.product']
        encountered_account_ids = values['l10n_ro_saft_stock_encountered_values']['account.account']
        for move in moves:
            movement_type = None
            quantity_factor = 0
            # Inventory count positive adjustment
            if move.location_usage not in ('internal', 'transit') and move.location_dest_usage in ('internal', 'transit'):
                movement_type = '110'
                quantity_factor = 1
            # Inventory count negative adjustment
            elif move.location_usage in ('internal', 'transit') and move.location_dest_usage not in ('internal', 'transit'):
                movement_type = '120'
                quantity_factor = -1
            # Internal Transfer
            else:
                movement_type = '80'
                quantity_factor = 0

            if move.picking_type_id:
                movement_type = move.picking_type_id.l10n_ro_stock_movement_type
                encountered_picking_type_ids.add(move.picking_type_id.id)

            values['movement_of_goods']['stock_movements'].append({
                'movement_reference': move.reference,
                'movement_date': move.date.date().isoformat(),
                'movement_type': movement_type,
                'stock_movement_lines': [],
            })
            for line_number, line in enumerate(move.move_line_ids, 1):
                values['movement_of_goods']['nb_stock_movement_lines'] += 1

                if quantity_factor == 1:
                    values['movement_of_goods']['total_quantity_received'] += line['quantity']
                elif quantity_factor == -1:
                    values['movement_of_goods']['total_quantity_issued'] += line['quantity']

                customer = line.picking_partner_id if line.picking_code == 'outgoing' else values['company'].partner_id
                supplier = line.picking_partner_id if line.picking_code == 'incoming' else values['company'].partner_id
                values['movement_of_goods']['stock_movements'][-1]['stock_movement_lines'].append({
                    'line_number': line_number,
                    'account_id': line.product_id.categ_id.property_stock_valuation_account_id.code,
                    'customer_id': self._l10n_ro_saft_get_registration_number(customer),
                    'supplier_id': self._l10n_ro_saft_get_registration_number(supplier),
                    'ship_to': {
                        'warehouse_id': line.location_dest_id.warehouse_id.id,
                        'location_id': line.location_dest_id.id,
                    } if line.location_dest_usage in ('internal', 'transit') else None,
                    'ship_from': {
                        'warehouse_id': line.location_id.warehouse_id.id,
                        'location_id': line.location_id.id,
                    } if line.location_usage in ('internal', 'transit') else None,
                    'product_code': line.product_id.default_code or line.product_id.code,
                    'lot': line.lot_id.id,
                    'quantity': line['quantity'],
                    'unit_of_measure': UOM_TO_UNECE_CODE.get(line.product_uom_id.get_external_id()[line.product_uom_id.id], 'C62'),
                    'uom_conversion_factor': safe_division(line.product_uom_id.factor_inv, line.product_id.uom_id.factor_inv),
                    'movement_subtype': movement_type,
                })
                encountered_uom_ids.add(line.product_uom_id.id)
                encountered_product_ids.add(line.product_id.id)
                encountered_account_ids.add(line.product_id.categ_id.property_stock_valuation_account_id.id)

    @api.model
    def _l10n_ro_saft_stock_fill_movement_types_values(self, options, values):
        if not options['l10n_ro_saft_required_sections']['master_files']['movement_type_table']:
            return

        values['movement_types'] = []
        picking_types = self.env['stock.picking.type'].browse(values['l10n_ro_saft_stock_encountered_values']['stock.picking.type']).sorted()
        if picking_types_without_l10n_ro_movement_type := picking_types.filtered(lambda p: not p.l10n_ro_stock_movement_type):
            raise RedirectWarning(
                self.env._("The Romanian authorities require a movement type for each picking type."),
                picking_types_without_l10n_ro_movement_type._get_records_action(),
                self.env._("View Picking Types"),
            )

        for picking_type in picking_types:
            values['movement_types'].append({
                'code': picking_type.l10n_ro_stock_movement_type,
                'name': picking_type.display_name,
            })

    def _get_all_partners(self, values, balance_result):
        # EXTENDS account_saft
        result = super()._get_all_partners(values, balance_result)
        if 'l10n_ro_saft_stock_encountered_values' in values:
            result |= self.env['res.partner'].browse(values['l10n_ro_saft_stock_encountered_values']['res.partner'])
        return result

    @api.model
    def _l10n_ro_saft_stock_fill_owners_values(self, options, values):
        if not options['l10n_ro_saft_required_sections']['master_files']['owners']:
            return

        values['owners'] = []
        owners = self.env['res.partner'].browse(values['l10n_ro_saft_stock_encountered_values']['res.partner']).sorted()
        owner_account_code = dict(values['l10n_ro_saft_stock_encountered_values']['owner_account_codes'])
        for owner in owners:
            values['owners'].append({
                'partner_id': owner.id,
                'owner_id': self._l10n_ro_saft_get_registration_number(owner),
                'account_id': owner_account_code[owner.id],
            })
