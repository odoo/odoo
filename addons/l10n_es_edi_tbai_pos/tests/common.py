from odoo.addons.point_of_sale.tests.common import CommonPosTest


class CommonPosEsEdiTest(CommonPosTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref("account.group_account_manager")
        cls.es_edi_edit_partner(cls)
        cls.es_edi_edit_product_templates(cls)

    def es_edi_edit_partner(self):
        self.partner_lowe.write(
            {
                "vat": "ESF35999705",
                "country_id": self.env.ref("base.es").id,
                "invoice_edi_format": None,
            }
        )

    def es_edi_edit_product_templates(self):
        self.ten_dollars_with_10_incl.write(
            {"taxes_id": self._get_tax_by_xml_id("s_iva21b").ids}
        )
