import re

from lxml import etree

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import file_open, float_compare, float_repr, float_round
from odoo.tools.xml_utils import _check_with_xsd

EQF_VERSION = '304'
EQF_KOD = 'QAIME_1'
EQF_XSD_PATH = 'l10n_az/data/xsd/QAIME_1.xsd'
EQF_STYLESHEET_PATH = 'l10n_az/data/qaime_1_stylesheet.xsl'
EQF_PROLOG = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<?xml-stylesheet type="text/xsl" href="#stylesheet"?>\n'
    b'<!DOCTYPE root [\n<!ATTLIST xsl:stylesheet\nid ID #REQUIRED>\n]>\n'
)
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'

# Tolerances of the xs:assert of the official schema, on the rows and on the totals.
ROW_TOLERANCE = 0.0001
TOTAL_TOLERANCE = 0.01


def _is_within(left, right, tolerance):
    """ Whether two amounts differ by at most tolerance, as the xs:assert of the official schema check them. """
    return float_compare(abs(left - right), tolerance, precision_digits=9) <= 0


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_l10n_az_eqf_generate(self):
        """ Generate the EQF (QAIME_1) XML of each invoice in self, attach it to the invoice with a chatter message
        and download it (as a zip when there are several invoices).
        Nothing is generated if any invoice is not ready: the reasons are shown in a dialog instead.
        """
        if alerts := self._l10n_az_eqf_get_alerts():
            wizard = self.env['l10n_az.eqf.error.wizard'].create({'alerts': alerts})
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Generate EQF"),
                'res_model': wizard._name,
                'res_id': wizard.id,
                'views': [(False, 'form')],
                'target': 'new',
            }

        xml_per_move = {}
        for move in self:
            xml_content = move._l10n_az_eqf_generate_xml()
            if xml_errors := self._l10n_az_eqf_validate_xml(xml_content):
                raise UserError(self.env._(
                    "The EQF generated for %(move)s does not comply with the QAIME_1 schema:\n%(errors)s",
                    move=move.name,
                    errors='\n'.join(xml_errors),
                ))
            xml_per_move[move] = xml_content

        attachments = self.env['ir.attachment']
        for move, xml_content in xml_per_move.items():
            attachment = self.env['ir.attachment'].create({
                'name': f"EQF_{move.name.replace('/', '_')}.xml",
                'res_model': move._name,
                'res_id': move.id,
                'raw': xml_content,
                'mimetype': 'application/xml',
            })
            move.message_post(
                body=self.env._("E-Qaimə Faktura (EQF) XML generated."),
                attachment_ids=attachment.ids,
            )
            attachments |= attachment

        if len(attachments) == 1:
            url = f'/web/content/{attachments.id}?download=true'
        else:
            url = f"/account/download_invoice_attachments/{','.join(str(attachment_id) for attachment_id in attachments.ids)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'download',
        }

    # -------------------------------------------------------------------------
    # CHECKS
    # -------------------------------------------------------------------------

    def _l10n_az_eqf_get_alerts(self):
        """ Collect every reason preventing the EQF generation of the invoices in self, one alert per reason with an
        action opening the records to fix.

        :return: a dict of alerts, as displayed by the actionable_errors widget; empty when all invoices are ready.
        """
        _ = self.env._
        alerts = {}

        def add_alert(key, records, message, action_text):
            if records:
                alerts[f'l10n_az_eqf_{key}'] = {
                    'level': 'danger',
                    'message': message,
                    'action_text': action_text,
                    'action': records._get_records_action(name=action_text),
                }

        def is_voen(vat):
            return bool(re.fullmatch(r'[0-9]{10}', vat or ''))

        add_alert(
            'invalid_companies',
            self.company_id.filtered(lambda company: company.account_fiscal_country_id.code != 'AZ' or not is_voen(company.vat)),
            _("The following company(s) must have Azerbaijan as fiscal country and a VÖEN of exactly 10 digits."),
            _("View Company(s)"),
        )
        add_alert(
            'invalid_customers',
            self.commercial_partner_id.filtered(lambda customer: (
                not is_voen(customer.vat)
                or customer.country_id.code != 'AZ'
                or not customer.street
                or not customer.city
            )),
            _("The following customer(s) must have a VÖEN of exactly 10 digits and an address in Azerbaijan, with a street and a city."),
            _("View Partner(s)"),
        )
        add_alert(
            'not_posted_invoices',
            self.filtered(lambda move: move.state != 'posted' or move.move_type != 'out_invoice'),
            _("The following entry(s) are not posted customer invoices."),
            _("View Entry(s)"),
        )
        add_alert(
            'invalid_currency',
            self.filtered(lambda move: move.currency_id.name != 'AZN'),
            _("The following invoice(s) are not in AZN."),
            _("View Invoice(s)"),
        )

        lines = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        add_alert(
            'invalid_product_code',
            lines.filtered(lambda line: not re.fullmatch(r'[0-9]{10}', line.l10n_az_eqf_product_code or '')).move_id,
            _("The following invoice(s) have lines without a National Goods/Services Code of exactly 10 digits."),
            _("View Invoice(s)"),
        )
        add_alert(
            'invalid_barcode',
            lines.product_id.filtered(lambda product: product.barcode and len(product.barcode) > 20),
            _("The barcode of the following product(s) exceeds 20 characters."),
            _("View Product(s)"),
        )
        vat_type_per_tax = {tax: tax._l10n_az_eqf_get_vat_type() for tax in lines.tax_ids}
        add_alert(
            'unreported_taxes',
            lines.filtered(lambda line: any(not vat_type_per_tax[tax] for tax in line.tax_ids)).move_id,
            _("The following invoice(s) have lines with taxes that do not belong to a tax group reported on the EQF."),
            _("View Invoice(s)"),
        )
        add_alert(
            'mixed_vat_treatments',
            lines.filtered(lambda line: (
                all(vat_type_per_tax[tax] for tax in line.tax_ids)
                and len({vat_type_per_tax[tax] for tax in line.tax_ids}) > 1
            )).move_id,
            _("The following invoice(s) have lines whose taxes have different EQF VAT Treatments; an EQF line accepts a single treatment."),
            _("View Invoice(s)"),
        )
        add_alert(
            'negative_lines',
            lines.filtered(lambda line: line.quantity <= 0 or line.price_subtotal < 0).move_id,
            _("The following invoice(s) have lines with a quantity or an amount that is not positive."),
            _("View Invoice(s)"),
        )
        # The unit price has at most 9 decimals, so c4 * c5 can miss c6 by more than the XSD tolerance on large quantities.
        add_alert(
            'unit_price_precision',
            self.filtered(lambda move: any(
                values['quantity'] > 0
                and not _is_within(values['quantity'] * values['price_unit'], values['subtotal'], ROW_TOLERANCE)
                for values in move._l10n_az_eqf_get_line_values()
            )),
            _(
                "The following invoice(s) have lines whose quantity is too large for the precision of the EQF unit price; "
                "split them into several invoice lines or use a larger unit of measure."
            ),
            _("View Invoice(s)"),
        )
        return alerts

    # -------------------------------------------------------------------------
    # XML GENERATION
    # -------------------------------------------------------------------------

    def _l10n_az_eqf_get_line_values(self):
        """ Compute the qaimeTable rows from the move's rounded tax details.

        :return: a list of dicts, one per product line, in sequence order.
        """
        self.ensure_one()
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        base_line_per_record = {
            base_line['record']: base_line
            for base_line in base_lines
            if base_line['record'] and base_line['record'].display_type == 'product'
        }
        product_lines = self.invoice_line_ids \
            .filtered(lambda line: line.display_type == 'product') \
            .sorted(lambda line: (line.sequence, line.id))

        lines_values = []
        for line in product_lines:
            tax_details = base_line_per_record[line]['tax_details']
            quantity = float_round(line.quantity, precision_digits=4)
            subtotal = float_round(tax_details['total_excluded_currency'], precision_digits=4)
            # The checks ensure all the taxes of the line share the same treatment.
            vat_type = line.tax_ids and line.tax_ids[0]._l10n_az_eqf_get_vat_type() or 'non_vat'
            if vat_type == 'taxable':
                vat_amount = float_round(
                    sum(tax_data['tax_amount_currency'] for tax_data in tax_details['taxes_data']),
                    precision_digits=4,
                )
            else:
                vat_amount = 0
            excise_rate = excise_amount = road_tax = 0
            total = subtotal + excise_amount
            lines_values.append({
                'line': line,
                'quantity': quantity,
                'price_unit': float_round(subtotal / quantity, precision_digits=9) if quantity else 0,
                'subtotal': subtotal,
                'excise_rate': excise_rate,
                'excise_amount': excise_amount,
                'total': total,
                'taxable': total if vat_type == 'taxable' else 0,
                'non_vat': total if vat_type == 'non_vat' else 0,
                'exempt': total if vat_type == 'exempt' else 0,
                'zero_rated': total if vat_type == 'zero_rated' else 0,
                'vat_amount': vat_amount,
                'road_tax': road_tax,
                'grand_total': total + vat_amount + road_tax,
            })
        return lines_values

    def _l10n_az_eqf_generate_xml(self):
        """ Build the EQF (QAIME_1) XML document of the invoice, without side effects.

        :return: the XML content as bytes.
        """
        self.ensure_one()
        customer = self.commercial_partner_id
        move = self.with_context(lang=customer.lang)
        company = move.company_id

        root = etree.Element('root', nsmap={'xsi': XSI_NS})
        root.set('version', EQF_VERSION)
        root.set('kod', EQF_KOD)
        root.set(f'{{{XSI_NS}}}noNamespaceSchemaLocation', 'QAIME_1.xsd')

        with file_open(EQF_STYLESHEET_PATH, 'rb') as stylesheet_file:
            root.append(etree.fromstring(stylesheet_file.read()))

        def add(parent, tag, text=None):
            node = etree.SubElement(parent, tag)
            if text is not None:
                node.text = text
            return node

        add(root, 'qaimeKime', customer.vat)
        add(root, 'qaimeKimden', company.vat)
        add(root, 'ds', '')
        add(root, 'dn', '')
        add(root, 'des', (move.name or '')[:150])
        add(root, 'des2', (move.ref or '')[:150])
        if location_address := company._l10n_az_eqf_get_location_address():
            add(root, 'ma', location_address)
        if location_code := company.partner_id._get_additional_identifier('AZ_EQF_LOCATION'):
            add(root, 'mk', location_code)

        product_node = add(root, 'product')
        table_node = add(product_node, 'qaimeTable')
        lines_values = move._l10n_az_eqf_get_line_values()
        for index, values in enumerate(lines_values):
            line = values['line']
            row = add(table_node, 'row')
            row.set('no', str(index))
            add(row, 'c1', line.l10n_az_eqf_product_code)
            add(row, 'c2', (line.product_id.name or line.name or '')[:300])
            add(row, 'c3', (line.product_uom_id or self.env.ref('uom.product_uom_unit')).name[:150])
            add(row, 'c4', float_repr(values['quantity'], 4))
            add(row, 'c5', float_repr(values['price_unit'], 9))
            for tag, key in (
                ('c6', 'subtotal'),
                ('c7', 'excise_rate'),
                ('c8', 'excise_amount'),
                ('c9', 'total'),
                ('c10', 'taxable'),
                ('c11', 'non_vat'),
                ('c12', 'exempt'),
                ('c13', 'zero_rated'),
                ('c14', 'vat_amount'),
                ('c15', 'road_tax'),
                ('c16', 'grand_total'),
            ):
                add(row, tag, float_repr(values[key], 4))
            add(row, 'c17', line.product_id.barcode or '0')
            add(row, 'productId', '0')

        def total(key):
            return sum(values[key] for values in lines_values)

        totals_row = add(add(product_node, 'qaimeYekunTable'), 'row')
        for tag, amount in (
            ('c1', total('subtotal')),
            ('c2', total('excise_amount')),
            ('c3', total('subtotal') + total('excise_amount')),
            ('c4', total('taxable')),
            ('c5', total('non_vat')),
            ('c6', total('exempt')),
            ('c7', total('zero_rated')),
            ('c8', total('vat_amount')),
            ('c9', total('grand_total')),
            ('c10', total('road_tax')),
        ):
            add(totals_row, tag, float_repr(float_round(amount, precision_digits=2), 2))

        add(root, 'qaimeKimeAd', customer.name)

        return EQF_PROLOG + etree.tostring(root, encoding='UTF-8', pretty_print=True)

    # -------------------------------------------------------------------------
    # XML VALIDATION
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_az_eqf_validate_xml(self, xml_content):
        """ Validate an EQF (QAIME_1) document: XSD 1.0 structure, then the XSD 1.1 assertions of the official schema
        (lxml only implements XSD 1.0, so they are re-implemented here).

        :param xml_content: the XML document as bytes.
        :return: a list of error messages; empty when the document is valid.
        """
        try:
            tree = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as error:
            return [str(error)]

        errors = []
        try:
            with file_open(EQF_XSD_PATH, 'rb') as xsd:
                _check_with_xsd(tree, xsd)
        except UserError as error:
            errors += str(error.args[0]).splitlines()
        return errors + self._l10n_az_eqf_check_xml_asserts(tree)

    @api.model
    def _l10n_az_eqf_check_xml_asserts(self, tree):
        """ Python re-implementation of every active xs:assert of the official EQF_MT.xsd, with the same
        tolerances. An assert is skipped when the @old attribute of its element is 1, as in the XSD.
        """
        _ = self.env._
        errors = []

        def value(node, tag):
            """ Numeric value of the child 'tag' of node, or None when it is missing or not a number. """
            child = node.find(tag) if node is not None else None
            if child is None or child.text is None:
                return None
            try:
                return float(child.text.strip())
            except ValueError:
                return None

        def is_within(left, right, tolerance):
            return left is not None and right is not None and _is_within(left, right, tolerance)

        def add_sums(*values):
            return None if any(val is None for val in values) else sum(values)

        rows = tree.findall('product/qaimeTable/row')
        for row in rows:
            if row.get('old') == '1':
                continue
            row_no = row.get('no')
            c = {f'c{i}': value(row, f'c{i}') for i in range(4, 17)}
            row_product = None if c['c4'] is None or c['c5'] is None else c['c4'] * c['c5']
            if not is_within(c['c6'], row_product, ROW_TOLERANCE):
                errors.append(_("qaimeTable row %s: c6 must be equal to c4 * c5.", row_no))
            if not is_within(c['c9'], add_sums(c['c6'], c['c8']), ROW_TOLERANCE):
                errors.append(_("qaimeTable row %s: c9 must be equal to c6 + c8.", row_no))
            vat_columns = [c['c10'], c['c11'], c['c12'], c['c13']]
            if not (
                all(column is not None and column == 0 for column in vat_columns)
                or is_within(c['c9'], add_sums(*vat_columns), ROW_TOLERANCE)
            ):
                errors.append(_("qaimeTable row %s: c9 must be equal to c10 + c11 + c12 + c13.", row_no))
            if not is_within(c['c16'], add_sums(c['c9'], c['c14'], c['c15']), ROW_TOLERANCE):
                errors.append(_("qaimeTable row %s: c16 must be equal to c9 + c14 + c15.", row_no))

        version = tree.get('version')
        try:
            version_ok = version is not None and float(version.strip()) >= 301
        except ValueError:
            version_ok = False
        if not version_ok:
            errors.append(_("The version attribute of the root must be at least 301."))

        if tree.get('old') == '1':
            return errors

        def rows_sum(tag):
            # sum() of an XPath node set: missing nodes are skipped, non-numeric ones make the assert fail.
            total = 0
            for row in rows:
                if row.find(tag) is not None:
                    row_value = value(row, tag)
                    if row_value is None:
                        return None
                    total += row_value
            return total

        def rows_products_sum(with_excise):
            total = 0
            for row in rows:
                factors = [value(row, 'c4'), value(row, 'c5')] + ([value(row, 'c8')] if with_excise else [])
                if any(factor is None for factor in factors):
                    return None
                total += factors[0] * factors[1] + (factors[2] if with_excise else 0)
            return total

        totals_row = tree.find('product/qaimeYekunTable/row')
        for tag, expected, formula in (
            ('c1', rows_products_sum(False), "sum(c4 * c5)"),
            ('c2', rows_sum('c8'), "sum(c8)"),
            ('c3', rows_products_sum(True), "sum(c4 * c5 + c8)"),
            ('c4', rows_sum('c10'), "sum(c10)"),
            ('c5', rows_sum('c11'), "sum(c11)"),
            ('c6', rows_sum('c12'), "sum(c12)"),
            ('c7', rows_sum('c13'), "sum(c13)"),
            ('c8', rows_sum('c14'), "sum(c14)"),
            ('c9', rows_sum('c16'), "sum(c16)"),
            ('c10', rows_sum('c15'), "sum(c15)"),
        ):
            if not is_within(value(totals_row, tag), expected, TOTAL_TOLERANCE):
                errors.append(_(
                    "qaimeYekunTable %(column)s must be equal to %(formula)s of the qaimeTable rows.",
                    column=tag,
                    formula=formula,
                ))
        return errors
