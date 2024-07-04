from odoo.addons.base.tests.test_reports import SPECIFIC_MODEL_DOMAINS


SPECIFIC_MODEL_DOMAINS.update({
    'account.report_original_vendor_bill': [('move_type', 'in', ('in_invoice', 'in_receipt'))],
})
