from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hr_process_type = fields.Selection(
        [
            ('P1', "P1: Issuing invoices for deliveries of goods and services according to purchase orders, based on contracts"),
            ('P2', "P2: Periodic invoicing for deliveries of goods and services based on contracts"),
            ('P3', "P3: Issuing invoices for delivery according to an independent purchase order"),
            ('P4', "P4: Prepayment (advance payment)"),
            ('P5', "P5: Payment on the spot (Sport payment)"),
            ('P6', "P6: Payment before delivery, based on purchase order"),
            ('P7', "P7: Issuing invoices with references to the delivery note"),
            ('P8', "P8: Issuing invoices with references to the shipping and receipt notes"),
            ('P9', "P9: Credits or invoices with negative amounts, issued for various reasons, including empty returns packaging"),
            ('P10', "P10: Issuing a corrective invoice (reversal/correction of invoice)"),
            ('P11', "P11: Issuing partial and final invoices"),
            ('P12', "P12: Self-issuance of invoice"),
            ('P99', "P99: Customer-defined process"),
        ],
        string="Business process type",
        default='P99'
    )
    l10n_hr_operator_oib = fields.Char("Operator OIB", default=False, store=True, compute='_compute_l10n_hr_operator_details')
    l10n_hr_operator_name = fields.Char("Operator Label", default=False, store=True, compute='_compute_l10n_hr_operator_details')

    @api.depends("company_id")
    def _compute_l10n_hr_operator_details(self):
        for move in self:
            if move.company_id.country_id.code == 'HR' and not move.l10n_hr_operator_name and not move.l10n_hr_operator_oib:
                move.l10n_hr_operator_oib = move.company_id.vat[2:]
                move.l10n_hr_operator_name = move.company_id.name

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        builder = super()._get_ubl_cii_builder_from_xml_tree(tree)
        customization_id = tree.find('{*}CustomizationID')
        if not tree.tag and not tree.find('{*}UBLVersionID') and customization_id is not None:
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0':
                return self.env['account.edi.xml.ubl_hr']
        else:
            return builder
