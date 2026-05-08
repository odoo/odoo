from odoo.addons.account.tests.common import TestTaxCommon


class TestWithholdTaxCommon(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set the withholding account so that we don't have to worry about it.
        cls.company_data['company'].withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'account_type': 'asset_current',
        })
        # We create a sequence for the same reason, so that we can forget about it.
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.outstanding_account = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'code': 'OSTP420',
            'account_type': 'asset_current'
        })
        cls.witthold_tax_section = cls.env['account.withholding.tax.section'].create({
            'name': 'Withholding Tax Section',
            'company_id': cls.company_data['company'].id,
            'withholding_sequence_id': cls.withholding_sequence.id,
        })
        cls.purchase_account = cls.env['account.account'].create({
            'code': '900000',
            'name': 'Product Sales',
            'account_type': 'income',
            'withholding_tax_section_id': cls.witthold_tax_section.id,
        })

    def percent_tax(self, amount, **kwargs):
        tax = super().percent_tax(amount, **kwargs)
        if tax.is_withholding_tax_on_payment and not tax.withholding_tax_section_id:
            tax.withholding_tax_section_id = self.witthold_tax_section
        return tax
