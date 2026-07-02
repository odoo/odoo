# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


class L10nHuEdiTestCommonReceive(L10nHuEdiTestCommon):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_huf = cls.env.ref('base.HUF')
        cls.tax_purchase_27 = cls.env['account.chart.template'].ref('V27')
        cls.tax_purchase_5 = cls.env['account.chart.template'].ref('V5')
        cls.tax_purchase_exempt = cls.env['account.chart.template'].ref('VKKS')
