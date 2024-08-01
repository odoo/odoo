from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


class TestPosTbaiCommon(TestEsEdiTbaiCommonGipuzkoa, TestPointOfSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
