from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_bis3 import CHORUS_PRO_PEPPOL_ID


class TestUblCiiCommonChorusPro(TestUblCiiCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_fr_chorus_pro = cls._create_partner_fr_chorus_pro()

    @classmethod
    def _create_partner_fr_chorus_pro(cls, **kwargs):
        chorus_eas, chorus_endpoint = CHORUS_PRO_PEPPOL_ID.split(":")
        return cls.env['res.partner'].create({
            **cls._create_partner_default_values(),
            'name': "Chorus Pro - Commune de Nantes",
            # Commune de Nantes
            'vat': "FR74214401093",
            'company_registry': "21440109300015",
            # Peppol ID for the AIFE (= Chorus Pro)
            'peppol_eas': chorus_eas,
            'peppol_endpoint': chorus_endpoint,
            'country_id': cls.env.ref('base.fr').id,
            **kwargs,
        })
