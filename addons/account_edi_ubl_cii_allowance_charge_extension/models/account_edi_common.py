from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = "account.edi.common"

    def _process_allowance_charge_nodes(self, tree, xpath_dict, invoice_line, billed_qty):
        """
        Override of the base method.

        Processes AllowanceCharge nodes of a UBL invoice line and populates
        `allowance_charge_taxes_list` with allowance/charge tax details.
        """
        allow_charge_amount = 0  # if positive: it's an allowance, if negative: it's a charge
        fixed_taxes_list = []
        allowance_charge_taxes_list = []
        allow_charge_nodes = tree.findall(xpath_dict['allowance_charge'])
        for allow_charge_el in allow_charge_nodes:
            charge_indicator = allow_charge_el.find(xpath_dict['allowance_charge_indicator'])
            amount = allow_charge_el.find(xpath_dict['allowance_charge_amount'])
            allowance_charge_percent = allow_charge_el.find(xpath_dict['allowance_charge_percent'])
            reason_code = allow_charge_el.find(xpath_dict['allowance_charge_reason_code'])
            reason = allow_charge_el.find(xpath_dict['allowance_charge_reason'])
            if amount is not None:

                # Handle Allowance/Charge Taxes: when exporting from Odoo, we use the allowance_charge node
                allowance_charge_tax_vals = {
                    'tax_amount': float(amount.text) / billed_qty,
                    'tax_reason_code': reason_code.text if reason_code is not None else None,
                    'tax_reason': reason.text if reason is not None else None,
                    'tax_percent': allowance_charge_percent.text if allowance_charge_percent is not None else None,
                    'charge_indicator': charge_indicator.text,
                }

                # We check if there is a tax present with given configuration,
                # if not then only we consider it as a line_discount.
                if (
                    reason_code is not None
                    and reason_code.text == '95'
                    and not self._import_retrieve_allowance_charge_tax(invoice_line, allowance_charge_tax_vals)
                ):
                    continue

                # We check if there is a tax present with given configuration,
                # if not then only we consider it as a fixed tax.
                if (
                    reason_code is not None
                    and reason_code.text in ('AEO', 'CAV')
                    and not self._import_retrieve_allowance_charge_tax(invoice_line, allowance_charge_tax_vals)
                ):
                    # Handle Fixed Taxes: when exporting from Odoo, we use the allowance_charge node
                    fixed_taxes_list.append({
                        'tax_name': reason.text,
                        'tax_amount': float(amount.text) / billed_qty,
                    })
                    continue

                allowance_charge_taxes_list.append(allowance_charge_tax_vals)
        return allow_charge_amount, fixed_taxes_list, allowance_charge_taxes_list

    def _get_fixed_tax_base_domain(self, invoice_line_form, fixed_tax_vals):
        """
        Restrict the search to real tax records only.
        Fixed taxes are matched by name, so this avoids incorrectly
        retrieving allowance/charge taxes.
        """
        return [
            *super()._get_fixed_tax_base_domain(invoice_line_form, fixed_tax_vals),
            ('ubl_cii_type', '=', 'tax')
        ]

    def _handle_allowance_charge_taxes(self, invoice_line_form, inv_line_vals):
        """
        Extend base method to implement logic to extract allowance/charge taxes from AllowanceCharge nodes.
        """
        # Handle Allowance/Charge Taxes
        for allowance_charge_tax_vals in inv_line_vals['allowance_charge_taxes_list']:
            tax = self._import_retrieve_allowance_charge_tax(invoice_line_form, allowance_charge_tax_vals)
            if not tax:
                # Nothing found: fix the price_unit s.t. line subtotal is matching the original invoice
                inv_line_vals['price_unit'] += allowance_charge_tax_vals['tax_amount']
            elif tax.price_include:
                inv_line_vals['taxes'].append(tax.id)
                inv_line_vals['price_unit'] += tax.amount
            else:
                inv_line_vals['taxes'].append(tax.id)
        # to handle fixed taxes (if any)
        return super()._handle_allowance_charge_taxes(invoice_line_form, inv_line_vals)

    def _import_retrieve_allowance_charge_tax(self, invoice_line_form, allowance_charge_tax_vals):
        """ Retrieve the Allowance/Charge tax at import, iteratively search for a tax:
        1. not price_include matching the reason, reason_code and amount
        2. not price_include matching the reason_code and amount
        3. not price_include matching the amount
        4. price_include matching the reason, reason_code and amount
        5. price_include matching the reason_code and amount
        6. price_include matching the amount
        """
        amount = allowance_charge_tax_vals['tax_percent'] if allowance_charge_tax_vals['tax_percent'] else allowance_charge_tax_vals['tax_amount']
        base_domain = [
            ('company_id', '=', invoice_line_form.company_id.id),
            ('amount', '=', amount),
            ('ubl_cii_type', '=', 'allowance_charge')
        ]
        for price_include in (False, True):
            for reason in (allowance_charge_tax_vals['tax_reason'], False):
                for reason_code in (allowance_charge_tax_vals['tax_reason_code'], False):
                    domain = base_domain + [('price_include', '=', price_include)]
                    if allowance_charge_tax_vals['charge_indicator'] == 'true':
                        domain += [('amount', '>=', 0)]
                        if reason_code:
                            domain.append(('ubl_cii_charge_reason_code', '=', reason_code))
                    else:
                        domain += [('amount', '<', 0)]
                        if reason_code:
                            domain.append(('ubl_cii_allowance_reason_code', '=', reason_code))
                    if reason:
                        domain.append(('ubl_cii_allowance_charge_reason', '=', reason))
                    tax = self.env['account.tax'].search(domain, limit=1)
                    if tax:
                        return tax
        return self.env['account.tax']

    def _get_tax_category_list(self, invoice, taxes):
        """
        Extend the base tax category list to handle AllowanceCharge taxes.

        Taxes marked as ``ubl_cii_type = 'allowance_charge'`` are converted into
        AllowanceCharge metadata, while remaining taxes are delegated to the base
        implementation for standard UBL/CII tax classification.
        """
        vals = []
        non_allowance_charge_taxes = self.env['account.tax']
        for tax in taxes:
            is_charge = tax.amount >= 0
            allowance_charge_reason_code = tax.ubl_cii_charge_reason_code if is_charge else tax.ubl_cii_allowance_reason_code
            if tax.ubl_cii_type == 'allowance_charge' and allowance_charge_reason_code:
                vals.append({
                    'id': 'charge' if is_charge else 'allowance',
                    'percent': tax.amount if tax.amount_type == 'percent' else False,
                    'charge_indicator': 'true' if is_charge else 'false',
                    'allowance_charge_reason_code': allowance_charge_reason_code,
                    'allowance_charge_reason': tax.ubl_cii_allowance_charge_reason
                })
            else:
                non_allowance_charge_taxes |= tax
        return super()._get_tax_category_list(invoice, non_allowance_charge_taxes) + vals
