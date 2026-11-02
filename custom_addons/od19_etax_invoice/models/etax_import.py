# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Import a supplier issued e-Tax Invoice / e-Receipt into a Vendor Bill.

The inbound flow mirrors the outbound one: the received XML is parsed and
validated against the ETDA schema, then expanded into a draft Vendor Bill that
carries the input VAT (ภาษีซื้อ) so the purchase can be reported in ภ.พ.30.
"""

import base64

from odoo import Command, fields, models
from odoo.exceptions import UserError

from ..lib import namespaces, xml_parser


class Od19EtaxImport(models.TransientModel):
    _name = "od19.etax.import"
    _description = "Import Purchase e-Tax Invoice"

    xml_file = fields.Binary(string="e-Tax XML File", required=True)
    xml_filename = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("parsed", "Parsed")],
        default="draft",
        required=True,
    )

    # ---- header read from the XML -------------------------------------
    document_type = fields.Selection(
        namespaces.DOCUMENT_TYPE_SELECTION, string="Document Type", readonly=True
    )
    document_name = fields.Char(string="Document Name", readonly=True)
    document_reference = fields.Char(string="Vendor Document No.", readonly=True)
    issue_date = fields.Date(string="Document Date", readonly=True)
    seller_name = fields.Char(string="Vendor Name", readonly=True)
    partner_vat = fields.Char(string="Vendor Tax ID", readonly=True)
    buyer_name = fields.Char(string="Buyer Name", readonly=True)
    buyer_vat = fields.Char(string="Buyer Tax ID", readonly=True)
    od19_buyer_is_own_company = fields.Boolean(
        string="Addressed to this Company", readonly=True
    )

    # ---- values prepared for the Vendor Bill --------------------------
    partner_id = fields.Many2one("res.partner", string="Vendor")
    journal_id = fields.Many2one(
        "account.journal",
        string="Purchase Journal",
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
    )
    ref = fields.Char(string="Bill Reference")
    invoice_date = fields.Date(string="Bill Date")

    line_ids = fields.One2many(
        "od19.etax.import.line", "wizard_id", string="Lines"
    )
    amount_untaxed = fields.Monetary(currency_field="currency_id", readonly=True)
    amount_tax = fields.Monetary(currency_field="currency_id", readonly=True)
    amount_total = fields.Monetary(currency_field="currency_id", readonly=True)
    move_id = fields.Many2one("account.move", string="Vendor Bill", readonly=True)

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------
    def action_parse(self):
        """Read, validate and expand the received XML onto the wizard."""
        self.ensure_one()
        if not self.xml_file:
            raise UserError(self.env._("กรุณาแนบไฟล์ XML e-Tax Invoice ก่อน"))
        try:
            data = xml_parser.parse(self._decode_xml(), validate=True)
        except xml_parser.ParseError as error:
            raise UserError(self.env._("ไฟล์ XML ไม่ถูกต้อง\n%s", error)) from error
        if data["errors"]:
            raise UserError(
                self.env._(
                    "ไฟล์ XML ไม่ผ่านการตรวจสอบตาม Schema ของ ETDA (ขมธอ.3-2560)\n%s",
                    "\n".join(data["errors"]),
                )
            )
        seller = data["seller"]
        buyer = data["buyer"]
        issue = xml_parser.parse_datetime(data["issue_datetime"])
        self.write({
            "state": "parsed",
            "document_type": data["document_type"],
            "document_name": data["name"],
            "document_reference": data["reference"],
            "issue_date": issue,
            "seller_name": seller.get("name"),
            "partner_vat": seller.get("tax_id"),
            "partner_id": self._resolve_vendor(seller).id,
            "buyer_name": buyer.get("name"),
            "buyer_vat": buyer.get("tax_id"),
            "od19_buyer_is_own_company": self._addressed_to_company(buyer),
            "currency_id": self._find_currency(data["currency"]).id,
            "journal_id": (self.journal_id or self._default_purchase_journal()).id,
            "ref": data["reference"],
            "invoice_date": issue or fields.Date.context_today(self),
            "line_ids": [Command.clear()] + [
                Command.create(self._line_vals(line)) for line in data["lines"]
            ],
            "amount_untaxed": data["totals"]["tax_basis_total"],
            "amount_tax": data["totals"]["tax_total"],
            "amount_total": data["totals"]["grand_total"],
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------
    def action_import(self):
        """Create the draft Vendor Bill carrying the input VAT."""
        self.ensure_one()
        if self.state != "parsed":
            raise UserError(
                self.env._("กรุณาตรวจสอบไฟล์ XML ก่อนสร้างใบกำกับภาษีซื้อ")
            )
        if self.move_id:
            raise UserError(self.env._("เอกสารนี้ถูกนำเข้าไปแล้ว"))
        if not self.line_ids:
            raise UserError(self.env._("ไม่พบรายการสินค้า/บริการในไฟล์ XML"))
        partner = self.partner_id or self._resolve_vendor({
            "name": self.seller_name,
            "tax_id": self.partner_vat,
        }, create=True)
        if not partner:
            raise UserError(self.env._("ไม่พบผู้ขาย (Vendor) กรุณาเลือกผู้ขาย"))
        lines = []
        for line in self.line_ids:
            tax = self._purchase_tax(line.tax_rate)
            lines.append(Command.create({
                "product_id": line.product_id.id,
                "name": line.name,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "tax_ids": [Command.set(tax.ids)],
            }))
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "company_id": self.company_id.id,
            "partner_id": partner.id,
            "journal_id": self.journal_id.id,
            "currency_id": self.currency_id.id,
            "ref": self.ref or self.document_reference,
            "invoice_date": self.invoice_date or fields.Date.context_today(self),
            "invoice_line_ids": lines,
        })
        self._attach_source_xml(move)
        self.move_id = move.id
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Vendor Bill"),
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def _attach_source_xml(self, move):
        """Keep the received XML on the bill as an audit attachment."""
        if not self.xml_file:
            return
        move.message_post(attachments=[
            (self.xml_filename or "vendor-etax.xml", self._decode_xml()),
        ])

    def _decode_xml(self):
        """Return the raw XML bytes of the attached file.

        A ``fields.Binary`` value is read back base64 encoded (as ``bytes`` or
        ``str``), so it is decoded once here for both the parser and the audit
        attachment.
        """
        raw = self.xml_file
        if not raw:
            return b""
        if isinstance(raw, str):
            raw = raw.encode("ascii", "ignore")
        return base64.b64decode(raw)

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------
    def _find_currency(self, code):
        if code:
            currency = self.env["res.currency"].search(
                [("name", "=", str(code).upper())], limit=1
            )
            if currency:
                return currency
        return self.company_id.currency_id

    def _default_purchase_journal(self):
        return self.env["account.journal"].search([
            ("type", "=", "purchase"),
            ("company_id", "=", self.company_id.id),
        ], limit=1)

    def _resolve_vendor(self, seller, create=False):
        """Return the vendor matching the seller party of the XML."""
        seller = seller or {}
        partner = self._find_partner_by_tin(seller.get("tax_id"))
        if not partner and not seller.get("tax_id") and seller.get("name"):
            partner = self.env["res.partner"].search(
                [("name", "=", seller["name"])], limit=1
            )
        if not partner and create:
            partner = self.env["res.partner"].create(self._vendor_vals(seller))
        return partner

    def _find_partner_by_tin(self, tax_id):
        needle = xml_parser.normalise_tax_id(tax_id)
        if not needle:
            return self.env["res.partner"]
        partners = self.env["res.partner"].search([("vat", "!=", False)])
        return partners.filtered(
            lambda partner: xml_parser.normalise_tax_id(partner.vat) == needle
        )[:1]

    def _vendor_vals(self, seller):
        address = seller.get("address") or {}
        country = self.env["res.country"].search(
            [("code", "=", (address.get("country_code") or "TH").upper())], limit=1
        )
        return {
            "name": seller.get("name") or self.env._("Unknown Vendor"),
            "vat": seller.get("tax_id"),
            "email": seller.get("email"),
            "phone": seller.get("phone"),
            "street": address.get("street"),
            "street2": address.get("street2"),
            "zip": address.get("zip"),
            "country_id": country.id or False,
            "supplier_rank": 1,
            "company_id": self.company_id.id,
        }

    def _addressed_to_company(self, buyer):
        """Return whether the buyer TIN of the XML is one of our companies."""
        buyer_tin = xml_parser.normalise_tax_id((buyer or {}).get("tax_id"))
        if not buyer_tin:
            return False
        own = self.env["res.company"].search([]).mapped("partner_id")
        return any(
            xml_parser.normalise_tax_id(partner.vat) == buyer_tin
            for partner in own
        )

    def _purchase_tax(self, rate):
        """Return the input tax of ``rate`` percent, if the company has one."""
        if not rate:
            return self.env["account.tax"]
        return self.env["account.tax"].search([
            ("company_id", "=", self.company_id.id),
            ("type_tax_use", "=", "purchase"),
            ("amount_type", "=", "percent"),
            ("price_include", "=", False),
            ("amount", "=", rate),
        ], limit=1)

    def _find_product(self, line):
        product = self.env["product.product"]
        if line.get("product_code"):
            product = product.search(
                [("default_code", "=", line["product_code"])], limit=1
            )
        if not product and line.get("name"):
            product = self.env["product.product"].search(
                [("name", "=", line["name"])], limit=1
            )
        return product

    def _line_vals(self, line):
        product = self._find_product(line)
        return {
            "name": line.get("name") or line.get("product_code")
            or self.env._("Imported line"),
            "product_code": line.get("product_code"),
            "product_id": product.id,
            "quantity": line.get("quantity") or 1.0,
            "price_unit": line.get("price_unit"),
            "tax_rate": line.get("tax_rate"),
            "tax_amount": line.get("tax_amount"),
            "price_subtotal": line.get("price_subtotal"),
        }


class Od19EtaxImportLine(models.TransientModel):
    _name = "od19.etax.import.line"
    _description = "Imported e-Tax Invoice Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "od19.etax.import", required=True, ondelete="cascade"
    )
    sequence = fields.Integer()
    name = fields.Char(string="Description", required=True)
    product_code = fields.Char()
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float(string="Unit Price")
    tax_rate = fields.Float(string="Tax Rate (%)")
    tax_amount = fields.Monetary(string="Tax", currency_field="currency_id")
    price_subtotal = fields.Monetary(string="Subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", related="wizard_id.currency_id"
    )
