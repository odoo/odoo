from unittest.mock import patch

from odoo import Command
from odoo.addons.l10n_es_edi_verifactu.tests.common import TestEsEdiVerifactuCommon
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestEsEdiVerifactuCommon, TestPointOfSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_es = cls.env['res.partner'].create({
            'name': 'ES Partner',
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.es').id,
            'invoice_edi_format': None,
        })
