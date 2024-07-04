from odoo.addons.base.tests.test_reports import SPECIFIC_MODEL_DOMAINS


SPECIFIC_MODEL_DOMAINS.update({
    'l10n_th.report_commercial_invoice': [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt'))],
})
