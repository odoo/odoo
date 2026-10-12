from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'eg_eta_edi_demo': {
                'label': self.env._("To ETA (Demo)"),
                'is_applicable': lambda move: move._is_l10n_eg_edi_applicable(mode='demo'),
                'help': self.env._("Simulate sending e-invoice to ETA."),
            },
            'eg_eta_edi_test': {
                'label': self.env._("To ETA (Pre-production)"),
                'is_applicable': lambda move: move._is_l10n_eg_edi_applicable(mode='preproduction'),
                'help': self.env._("Send the e-invoice to Egyptian EDI (ETA) Pre-production environment"),
            },
            'eg_eta_edi': {
                'label': self.env._("To ETA"),
                'is_applicable': lambda move: move._is_l10n_eg_edi_applicable(mode='production'),
                'help': self.env._("Send the e-invoice to Egyptian EDI (ETA) Production environment"),
            },
        })
        return res

    @api.model
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        eg_moves = moves.filtered(
            lambda m: (
                'eg_eta_edi' in moves_data[m]['extra_edis']
                or 'eg_eta_edi_test' in moves_data[m]['extra_edis']
                or 'eg_eta_edi_demo' in moves_data[m]['extra_edis']
            ),
        )
        if not eg_moves:
            return alerts
        alerts.update(eg_moves._get_l10n_eg_edi_alerts())
        return alerts

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        eg_moves = self.env['account.move']
        eg_demo_moves = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            if 'eg_eta_edi_demo' in invoice_data['extra_edis']:
                eg_demo_moves |= invoice
            elif 'eg_eta_edi_test' in invoice_data['extra_edis'] or 'eg_eta_edi' in invoice_data['extra_edis']:
                eg_moves |= invoice
        if eg_moves:
            eg_moves._l10n_eg_edi_send_invoices_in_batch(len(eg_moves) == 1)
        if eg_demo_moves:
            eg_demo_moves._l10n_eg_edi_simulate_send_invoices(len(eg_demo_moves) == 1)
