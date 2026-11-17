from odoo import api, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt


class AccountEdiXmlUbl21(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_21'

    @api.model
    def _ubl_add_line_allowance_charge_nodes(self, vals):
        super()._ubl_add_line_allowance_charge_nodes(vals)
        product = vals['base_line']['product_id']
        if not product.l10n_fr_border_reference:
            return

        line_node = vals['line_node']
        for rate in (product.l10n_fr_rate_id, product.l10n_fr_regional_rate_id):
            if rate:
                tax_vals = next((vals for vals in vals['base_line']['tax_details']['taxes_data'] if vals['tax'] == rate), None)
                line_node['cac:AllowanceCharge'].append({
                    '_currency': vals['currency_id'],
                    'cbc:ChargeIndicator': {'_text': 'true'},
                    'cbc:AllowanceChargeReasonCode': {'_text': 'ZZZ'},
                    'cbc:AllowanceChargeReason': {
                        '_text': f"Octroi de Mer{' regional' if rate.tax_group_id.l10n_fr_om_rate == 'regional' else ''} ({rate.amount}%)",
                    },
                    'cbc:MultiplierFactorNumeric': {'_text': rate.amount},
                    'cbc:Amount': {
                        '_text': FloatFmt(tax_vals['tax_amount'], max_dp=vals['currency_dp']),
                        'currencyID': vals['currency_id'].name,
                    },
                    'cbc:BaseAmount': {
                        '_text': FloatFmt(tax_vals['base_amount'], max_dp=vals['currency_dp']),
                        'currencyID': vals['currency_id'].name,
                    },
                })

    @api.model
    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        super()._ubl_add_line_item_commodity_classification_nodes(vals)
        product = vals['base_line']['product_id']
        if not product.l10n_fr_border_reference:
            return

        vals['line_node']['cac:Item']['cac:CommodityClassification'].append({
            'cbc:ItemClassificationCode': {
                '_text': product.l10n_fr_border_reference.code,
                'listID': 'CN',
            },
        })

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if tax_data and tax_data['tax'].tax_group_id.l10n_fr_om_rate:
            grouping_key['is_allowance_charge'] = True

        return grouping_key

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        grouping_key = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)
        if tax_data and tax_data['tax'].tax_group_id.l10n_fr_om_rate:
            grouping_key['tax_total_key']['is_allowance_charge'] = True

        return grouping_key

    def _import_ubl_create_allowance_tax(self, allowance_charge_elem, company_id):
        is_tax_created = super()._import_ubl_create_allowance_tax(allowance_charge_elem, company_id)
        if is_tax_created:
            return is_tax_created

        multiplier_factor_numeric = allowance_charge_elem.findtext('.//{*}MultiplierFactorNumeric')
        if not multiplier_factor_numeric:
            return False

        multiplier_factor_numeric = float(multiplier_factor_numeric)
        allowance_charge_reason = allowance_charge_elem.findtext('.//{*}AllowanceChargeReason')
        is_regional_sea_grant = 'région' in allowance_charge_reason or 'region' in allowance_charge_reason
        tax_count = self.env['account.tax'].search_count([
            ('amount', '=', multiplier_factor_numeric),
            ('company_id', 'in', (False, company_id)),
            ('type_tax_use', '=', 'none'),
            ('tax_group_id.l10n_fr_om_rate', '=', 'regional' if is_regional_sea_grant else 'general')
        ])
        return tax_count == 1

    def _import_ubl_invoice_line_add_taxes_values(self, collected_values):
        super()._import_ubl_invoice_line_add_taxes_values(collected_values)
        line_tree = collected_values['line_tree']
        for allowance_charge_elem in line_tree.iterfind('./{*}AllowanceCharge'):
            charge_indicator = allowance_charge_elem.findtext('.//{*}ChargeIndicator')
            if charge_indicator.lower() != 'true':
                continue

            multiplier_factor_numeric = allowance_charge_elem.findtext('.//{*}MultiplierFactorNumeric')
            if not multiplier_factor_numeric:
                continue

            multiplier_factor_numeric = float(multiplier_factor_numeric)
            allowance_charge_reason = allowance_charge_elem.findtext('.//{*}AllowanceChargeReason')
            is_regional_sea_grant = 'région' in allowance_charge_reason or 'region' in allowance_charge_reason
            tax = self.env['account.tax'].search([
                ('amount', '=', multiplier_factor_numeric),
                ('company_id', 'in', (False, collected_values['company'].id)),
                ('type_tax_use', '=', 'none'),
                ('tax_group_id.l10n_fr_om_rate', '=', 'regional' if is_regional_sea_grant else 'general')
            ], limit=2)
            if len(tax) > 1:
                continue

            collected_values['taxes_values'].append({
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'amount': multiplier_factor_numeric,
                'ubl_cii_tax_category_code': False,
                'tax_group_id': tax.tax_group_id.id,
                'invoice_predictive': {
                    'invoice': collected_values['invoice'],
                    'name': collected_values['to_write'].get('name'),
                    'partner': collected_values['customer_values'].get('customer'),
                }
            })
