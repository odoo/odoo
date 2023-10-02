# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_round

from base64 import b64encode
from functools import partial
from markupsafe import Markup


class L10nHuNavAdatellenorzesWiz(models.TransientModel):
    _name = "l10n_hu.nav_aea_wiz"
    _description = "NAV Adóhatósági Ellenőrzési Adatszolgáltatás Wizard"

    # feltételek
    name_from = fields.Char("Number From")
    name_to = fields.Char("Number To")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    date_field = fields.Selection(
        [
            ("invoice_date", "Issue Date"),
            ("l10n_hu_delivery_date", "Delivery Date"),
            ("date", "Accounting Date"),
        ],
        string="Date field",
        default="invoice_date",
        required=True,
    )
    company_ids = fields.Many2many(
        "res.company",
        string="Companies to export",
        default=lambda s: s.env.company.filtered(lambda c: c.partner_id.country_id.code == "HU"),
    )
    use_cdata = fields.Boolean("Render with CDATA marker", default=True)

    name = fields.Char("XML File Name", readonly=True)
    data = fields.Binary("XML File Data", readonly=True)
    state = fields.Selection([("draft", "draft"), ("done", "done")], string="Status", default="draft", required=True)

    def do_generate(self):
        self.ensure_one()

        invoice_tbl = self.env["account.move"].sudo()
        nav_comm_tbl = self.env["l10n_hu.nav_communication"]
        qweb_tbl = self.env["ir.qweb"]
        edi_format_tbl = self.env["account.edi.format"]

        if not (self.name_from or self.name_to or self.date_from or self.date_to):
            raise UserError(_("Please enter at least one search term!"))
        if not self.company_ids:
            raise UserError(_("Please specify at least one company!"))

        domain = [
            # only out invoices
            ("move_type", "in", ("out_invoice", "out_refund")),
            # only issued invoices
            ("state", "=", "posted"),
            # customer only hungarian
            ("partner_id.commercial_partner_id.country_id.code", "=", "HU"),
        ]
        # issuer
        if len(self.company_ids) == 1:
            domain.append(("company_id", "=", self.company_ids.id))
        elif len(self.company_ids) > 1:
            domain.append(("company_id", "in", self.company_ids.ids))
        else:
            # every hungarian company
            domain.append(("company_id.account_fiscal_country_id.code", "=", "HU"))

        # search for number
        if self.name_from:
            domain.append(("name", ">=", self.name_from))
        if self.name_to:
            domain.append(("name", "<=", self.name_to))
        if self.date_from:
            domain.append((self.date_field, ">=", self.date_from))
        if self.date_to:
            domain.append((self.date_field, "<=", self.date_to))
        invoices = invoice_tbl.search(domain)

        if not invoices:
            raise UserError(_("No invoice to export!"))

        def format_cdata(value, use_cdata):
            if use_cdata:
                return Markup("<![CDATA[{0}]]>").format(value)
            else:
                return f"{value}"

        def format_num(value):
            if isinstance(value, float):
                return "{:.2f}".format(float_round(value, precision_digits=2))
            return f"{value}"

        render_datas = {
            "invoices": invoices,
            "invoice_xmls": [
                qweb_tbl._render(
                    "l10n_hu_edi.nav_AEA_invoice_xml",
                    {
                        **edi_format_tbl._l10n_hu_edi_generate_xml_data(i),
                        "format_text": partial(format_cdata, use_cdata=self.use_cdata),
                        "format_num": format_num,
                    },
                )
                for i in invoices
            ],
            "export_date": fields.Date.context_today(self),
            "format_text": partial(format_cdata, use_cdata=self.use_cdata),
            "format_bool": nav_comm_tbl._gen_nav_format_bool,
            "format_date": nav_comm_tbl._gen_nav_format_date,
            "format_num": format_num,
        }

        xml_content = Markup("<?xml version='1.0' encoding='UTF-8'?>") + qweb_tbl._render(
            "l10n_hu_edi.nav_AEA_xml", render_datas
        )

        act_time = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        file_name = f"nav_aea_export_{act_time.strftime('%Y%m%d%H%M%S')}.xml"

        self.write(
            {
                "state": "done",
                "data": b64encode(xml_content.encode("UTF-8")),
                "name": file_name,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
