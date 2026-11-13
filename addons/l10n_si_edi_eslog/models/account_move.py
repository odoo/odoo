from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Fields required for correctly generating e-Slog documents
    l10n_si_process_type = fields.Selection(
        [
            ('P1', "P1: Invoicing of deliveries of goods and services against purchase orders, based on a contract"),
            ('P2', "P2: Invoicing deliveries of goods and services based on a contract"),
            ('P3', "P3: Invoicing the delivery of an incidental purchase order"),
            ('P4', "P4: Pre-payment"),
            ('P5', "P5: Spot payment"),
            ('P6', "P6: Payment in advance of delivery"),
            ('P7', "P7: Invoices with references to a despatch advice"),
            ('P8', "P8: Invoices with references to a despatch advice and a receiving advice"),
            ('P9', "P9:  Credit notes or invoices with negative amounts, issued for a variety of reasons including the return of empty packaging"),
            ('P10', "P10: Corrective invoicing (cancellation/correction of an invoice)"),
            ('P11', "P11: Partial and final invoicing"),
            ('P12', "P12:  Self billing"),
        ],
        string="Slovenian Business Process Type",
        compute='_compute_l10n_si_process_type',
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_si_reference_type = fields.Selection(
        [
            ('AEP', "Project number"),
            ('CT', "Contact number"),
            ('ON', "Order number (customer)"),
            ('VN', "Order number (supplier)"),
            ('ALO', "Receiving advice number"),
            ('AAK', "Dispatch advice number"),
            ('GC', "Government contract number"),
            ('ATS', "External object reference"),
            ('OI', "Previous invoice number"),
            ('PQ', "Payment reference"),
        ],
        string="Reference Type",
        compute='_compute_l10n_si_reference_type',
        store=True,
        readonly=False,
        copy=False,
    )

    @api.depends('move_type', 'l10n_si_process_type')
    def _compute_l10n_si_process_type(self):
        for move in self:
            if not move.l10n_si_process_type:
                if move.move_type == 'out_refund':
                    move.l10n_si_process_type = 'P9'
                elif move.move_type == 'out_invoice':
                    move.l10n_si_process_type = 'P1'

    @api.depends('move_type', 'l10n_si_process_type')
    def _compute_l10n_si_reference_type(self):
        for move in self:
            if not move.l10n_si_reference_type:
                if move.move_type == 'out_refund':
                    move.l10n_si_reference_type = 'OI'
                elif move.move_type == 'out_invoice':
                    move.l10n_si_reference_type = 'ON'

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}M_INVOIC')
        if customization_id is not None:
            return self.env['account.edi.xml.eslog']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
