# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBrEDIXMLImport(AccountTestInvoicingCommon, ProductVariantsCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("br")
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_purchase"].with_context(default_move_type="in_invoice")

    def _create_invoice_from_xml(self, filename, old=None, new=None):
        """Loads filename into an attachment and runs the import wizard. Optional old and new can be used to replace
        strings."""
        with file_open(f"l10n_br_edi/tests/{filename}", mode="rb") as fd:
            import_content = fd.read()

        if old and new:
            import_content = import_content.replace(old.encode(), new.encode())

        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.xml",
                "raw": import_content,
            }
        )

        return self.journal._create_document_from_attachment(attachment.ids)

    def test_l10n_br_edi_xml_import_1(self):
        vendor = self.env["res.partner"].create(
            {
                "name": "test",
                "l10n_latam_identification_type_id": self.env.ref("l10n_br.cnpj").id,
                "vat": "37.842.696/0001-03",
            }
        )
        transporter = self.env["res.partner"].create(
            {
                "name": "transporter",
                "l10n_latam_identification_type_id": self.env.ref("l10n_br.cnpj").id,
                "vat": "03007331000141",
            }
        )
        product = self.env["product.template"].create({"name": "test product"})
        self.env["product.supplierinfo"].create(
            {
                "partner_id": vendor.id,
                "product_tmpl_id": product.id,
                "product_code": "60953-09",
            }
        )

        invoice = self._create_invoice_from_xml("NFe3224023.xml")

        self.assertRecordValues(
            invoice,
            [
                {
                    "l10n_latam_document_type_id": self.env.ref("l10n_br.dt_55").id,
                    "l10n_latam_document_number": "38136",
                    "invoice_date": fields.Date.to_date("2024-02-07"),
                    "delivery_date": fields.Date.to_date("2024-02-07"),
                    "partner_id": vendor.id,
                    "l10n_br_access_key": "NFe32240237842696000103550010000381361702937325",
                    "l10n_br_edi_payment_method": "17",
                    "l10n_br_edi_freight_model": "Thirdparty",
                    "l10n_br_edi_transporter_id": transporter.id,
                }
            ],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "product_id": product.product_variant_id.id,
                    "quantity": 1.0,
                    "price_unit": 127.27,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                    "is_imported": True,
                }
            ],
        )

    def test_l10n_br_edi_xml_import_1_autocreate_partner(self):
        """Test the auto-creation of partner."""
        self.assertRecordValues(
            self._create_invoice_from_xml("NFe3224023.xml").partner_id,
            [
                {
                    "is_company": True,
                    "vat": "37842696000103",
                    "l10n_latam_identification_type_id": self.env.ref("l10n_br.cnpj").id,
                    "name": "A G CANDIDO LOJA DE DEPARTAMENTO EIRELI",
                    "street_name": "Rua Josias Cerutti",
                    "street_number": "2",
                    "street2": "Praia do Morro",
                    "street_number2": "Nao consta",
                    "city_id": self.env.ref("l10n_br.city_br_243").id,
                    "state_id": self.env.ref("base.state_br_es").id,
                    "zip": "29216600",
                    "country_id": self.env.ref("base.br").id,
                    "phone": "0028998812093",
                    "l10n_br_ie_code": "083672591",
                }
            ],
        )

    def test_l10n_br_edi_xml_import_1_import_non_existent_state(self):
        """Test that the city is still found when a non-existent state is specified."""
        self.assertRecordValues(
            self._create_invoice_from_xml("NFe3224023.xml", old="<UF>ES</UF>", new="<UF>XX</UF>").partner_id,
            [
                {
                    "city_id": self.env.ref("l10n_br.city_br_243").id,
                    "state_id": False,
                }
            ],
        )

    def test_l10n_br_edi_xml_import_default_code(self):
        """Test if products are matched using default_code."""
        product = self.env["product.template"].create({"name": "test product", "default_code": "60953-09"})
        self.assertRecordValues(
            self._create_invoice_from_xml("NFe3224023.xml").invoice_line_ids,
            [{"product_id": product.product_variant_id.id}],
        )

    def test_l10n_br_edi_xml_import_supplierinfo(self):
        """Supplierinfo should only match if it refers to exactly one variant."""
        vendor = self.env["res.partner"].create(
            {
                "name": "test",
                "l10n_latam_identification_type_id": self.env.ref("l10n_br.cnpj").id,
                "vat": "37.842.696/0001-03",
            }
        )
        supplierinfo = self.env["product.supplierinfo"].create(
            {
                "partner_id": vendor.id,
                "product_tmpl_id": self.product_template_sofa.id,
                "product_code": "60953-09",
            }
        )

        # This template has >1 variants, so we shouldn't match based on supplierinfo.
        self.assertRecordValues(
            self._create_invoice_from_xml("NFe3224023.xml").invoice_line_ids,
            [{"product_id": False}],
        )

        self.product_template_sofa.product_variant_ids[1:].write({"active": False})
        # These are not automatically invalidated when you write on the variants
        self.product_template_sofa.invalidate_recordset(["product_variant_count"])
        supplierinfo.invalidate_recordset(["product_variant_count"])

        # Now that there's only one variant it should match.
        self.assertRecordValues(
            self._create_invoice_from_xml("NFe3224023.xml").invoice_line_ids,
            [{"product_id": self.product_template_sofa.product_variant_id.id}],
        )

    def test_l10n_br_edi_xml_import_2(self):
        invoice = self._create_invoice_from_xml("NFe4124030.xml")
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "name": "ALCOOL 70 GRAUS SUPER VALE 1LT 19553",
                    "quantity": 3.0,
                    "price_unit": 6.07,
                    "price_total": 18.21,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                },
                {
                    "name": "COPO 180ML TRANSP PP COPOBRAS 100UN CFT180 13685",
                    "quantity": 6.0,
                    "price_unit": 5.63,
                    "price_total": 33.78,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,  # PCT
                },
                {
                    "name": "COPO 400ML TRANSP LISO PP COPOBRAS 50UN PPT440 (TAMPAS 2414/3901/3902) 13071",
                    "quantity": 4.0,
                    "price_unit": 11.71,
                    "price_total": 46.84,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,  # PCT
                },
                {
                    "name": "GUARDANAPO BRANCO F.DUPLA ROSA 32 X 32CM 50UN 12803",
                    "quantity": 4.0,
                    "price_unit": 7.63,
                    "price_total": 30.52,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,  # PCT
                },
                {
                    "name": "PAPEL HIG. CAI-CAI F. DUPLA MADDU 8.000FL 18217",
                    "quantity": 2.0,
                    "price_unit": 130.73,
                    "price_total": 261.46,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,  # CX
                },
                {
                    "name": "TOALHA PAPEL INTERFOLHA F.DUPLA MADDU 22 X 20CM 2.000FL 38GR 18223",
                    "quantity": 4.0,
                    "price_unit": 101.82,
                    "price_total": 407.28,
                    "product_uom_id": self.env.ref("uom.product_uom_unit").id,  # CX
                },
            ],
        )
