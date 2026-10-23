from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericAR(TestGenericLocalization):

    _pos_partner_pos_form_fields = ['vat', 'additional_identifiers', 'l10n_ar_afip_responsibility_type_id']
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ar')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.write({
            'country_id': cls.env.ref('base.ar').id,
            'vat': False,
            'additional_identifiers': {'AR_SIGD': '0'},
            'l10n_ar_afip_responsibility_type_id': cls.env.ref('l10n_ar.res_CF').id,
        })
