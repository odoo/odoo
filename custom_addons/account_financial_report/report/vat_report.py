# Copyright  2018 Forest and Biomass Romania
# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import operator

from odoo import api, models


class VATReport(models.AbstractModel):
    _name = "report.account_financial_report.vat_report"
    _description = "Vat Report Report"

    def _get_tax_data(self, tax_ids):
        taxes = self.env["account.tax"].browse(tax_ids)
        tax_data = {}
        for tax in taxes:
            tax_data.update(
                {
                    tax.id: {
                        "id": tax.id,
                        "name": tax.name,
                        "tax_group_id": tax.tax_group_id.id,
                        "type_tax_use": tax.type_tax_use,
                        "amount_type": tax.amount_type,
                        "tags_ids": tax.invoice_repartition_line_ids.tag_ids.ids,
                    }
                }
            )
        return tax_data

    @api.model
    def _get_tax_report_domain(self, company_id, date_from, date_to, only_posted_moves):
        domain = [
            ("company_id", "=", company_id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("tax_line_id", "!=", False),
        ] + self.env["account.move.line"]._get_tax_exigible_domain()
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        return domain

    @api.model
    def _get_net_report_domain(self, company_id, date_from, date_to, only_posted_moves):
        domain = [
            ("company_id", "=", company_id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ] + self.env["account.move.line"]._get_tax_exigible_domain()
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        return domain

    def _get_vat_report_data(self, company_id, date_from, date_to, only_posted_moves):
        tax_domain = self._get_tax_report_domain(
            company_id, date_from, date_to, only_posted_moves
        )
        ml_fields = self._get_ml_fields_vat_report()
        tax_move_lines = self.env["account.move.line"].search_read(
            domain=tax_domain,
            fields=ml_fields,
        )
        net_domain = self._get_net_report_domain(
            company_id, date_from, date_to, only_posted_moves
        )
        taxed_move_lines = self.env["account.move.line"].search_read(
            domain=net_domain,
            fields=ml_fields,
        )
        taxed_move_lines = list(filter(lambda d: d["tax_ids"], taxed_move_lines))
        vat_data = []
        for tax_move_line in tax_move_lines:
            vat_data.append(
                {
                    "net": 0.0,
                    "tax": tax_move_line["balance"],
                    "tax_line_id": tax_move_line["tax_line_id"][0],
                }
            )
        for taxed_move_line in taxed_move_lines:
            for tax_id in taxed_move_line["tax_ids"]:
                vat_data.append(
                    {
                        "net": taxed_move_line["balance"],
                        "tax": 0.0,
                        "tax_line_id": tax_id,
                    }
                )
        tax_ids = list(map(operator.itemgetter("tax_line_id"), vat_data))
        tax_ids = list(set(tax_ids))
        tax_data = self._get_tax_data(tax_ids)
        return vat_data, tax_data

    def _get_tax_group_data(self, tax_group_ids):
        tax_groups = self.env["account.tax.group"].search_fetch(
            [("id", "in", tax_group_ids)], ["name", "sequence"]
        )
        tax_group_data = {}
        for tax_group in tax_groups:
            tax_group_data.update(
                {
                    tax_group.id: {
                        "id": tax_group.id,
                        "name": tax_group.name,
                        "code": str(tax_group.sequence),
                    }
                }
            )
        return tax_group_data

    def _get_vat_report_group_data(self, vat_report_data, tax_data, tax_detail):
        vat_report = {}
        for tax_move_line in vat_report_data:
            tax_id = tax_move_line["tax_line_id"]
            if tax_data[tax_id]["amount_type"] == "group":
                pass
            else:
                tax_group_id = tax_data[tax_id]["tax_group_id"]
                if tax_group_id not in vat_report.keys():
                    vat_report[tax_group_id] = {}
                    vat_report[tax_group_id]["net"] = 0.0
                    vat_report[tax_group_id]["tax"] = 0.0
                    vat_report[tax_group_id][tax_id] = dict(tax_data[tax_id])
                    vat_report[tax_group_id][tax_id].update({"net": 0.0, "tax": 0.0})
                else:
                    if tax_id not in vat_report[tax_group_id].keys():
                        vat_report[tax_group_id][tax_id] = dict(tax_data[tax_id])
                        vat_report[tax_group_id][tax_id].update(
                            {"net": 0.0, "tax": 0.0}
                        )
                vat_report[tax_group_id]["net"] += tax_move_line["net"]
                vat_report[tax_group_id]["tax"] += tax_move_line["tax"]
                vat_report[tax_group_id][tax_id]["net"] += tax_move_line["net"]
                vat_report[tax_group_id][tax_id]["tax"] += tax_move_line["tax"]
        tax_group_data = self._get_tax_group_data(list(vat_report.keys()))
        vat_report_list = []
        for tax_group_id in vat_report.keys():
            vat_report[tax_group_id]["name"] = tax_group_data[tax_group_id]["name"]
            vat_report[tax_group_id]["code"] = tax_group_data[tax_group_id]["code"]
            if tax_detail:
                vat_report[tax_group_id]["taxes"] = []
                for tax_id in vat_report[tax_group_id]:
                    if isinstance(tax_id, int):
                        vat_report[tax_group_id]["taxes"].append(
                            vat_report[tax_group_id][tax_id]
                        )
            vat_report_list.append(vat_report[tax_group_id])
        return vat_report_list

    def _get_tags_data(self, tags_ids):
        tags = self.env["account.account.tag"].search_fetch(
            [("id", "in", tags_ids)], ["name"]
        )
        tags_data = {}
        for tag in tags:
            tags_data.update({tag.id: {"code": "", "name": tag.name}})
        return tags_data

    def _get_vat_report_tag_data(self, vat_report_data, tax_data, tax_detail):
        vat_report = {}
        for tax_move_line in vat_report_data:
            tax_id = tax_move_line["tax_line_id"]
            tags_ids = tax_data[tax_id]["tags_ids"]
            if tax_data[tax_id]["amount_type"] == "group":
                continue
            else:
                if tags_ids:
                    for tag_id in tags_ids:
                        if tag_id not in vat_report.keys():
                            vat_report[tag_id] = {}
                            vat_report[tag_id]["net"] = 0.0
                            vat_report[tag_id]["tax"] = 0.0
                            vat_report[tag_id][tax_id] = dict(tax_data[tax_id])
                            vat_report[tag_id][tax_id].update({"net": 0.0, "tax": 0.0})
                        else:
                            if tax_id not in vat_report[tag_id].keys():
                                vat_report[tag_id][tax_id] = dict(tax_data[tax_id])
                                vat_report[tag_id][tax_id].update(
                                    {"net": 0.0, "tax": 0.0}
                                )
                        vat_report[tag_id][tax_id]["net"] += tax_move_line["net"]
                        vat_report[tag_id][tax_id]["tax"] += tax_move_line["tax"]
                        vat_report[tag_id]["net"] += tax_move_line["net"]
                        vat_report[tag_id]["tax"] += tax_move_line["tax"]
        tags_data = self._get_tags_data(list(vat_report.keys()))
        vat_report_list = []
        for tag_id in vat_report.keys():
            vat_report[tag_id]["name"] = tags_data[tag_id]["name"]
            vat_report[tag_id]["code"] = tags_data[tag_id]["code"]
            if tax_detail:
                vat_report[tag_id]["taxes"] = []
                for tax_id in vat_report[tag_id]:
                    if isinstance(tax_id, int):
                        vat_report[tag_id]["taxes"].append(vat_report[tag_id][tax_id])
            vat_report_list.append(vat_report[tag_id])
        return vat_report_list

    def _get_report_values(self, docids, data):
        wizard_id = data["wizard_id"]
        company = self.env["res.company"].browse(data["company_id"])
        company_id = data["company_id"]
        date_from = data["date_from"]
        date_to = data["date_to"]
        based_on = data["based_on"]
        tax_detail = data["tax_detail"]
        only_posted_moves = data["only_posted_moves"]
        vat_report_data, tax_data = self._get_vat_report_data(
            company_id, date_from, date_to, only_posted_moves
        )
        if based_on == "taxgroups":
            vat_report = self._get_vat_report_group_data(
                vat_report_data, tax_data, tax_detail
            )
        else:
            vat_report = self._get_vat_report_tag_data(
                vat_report_data, tax_data, tax_detail
            )
        return {
            "doc_ids": [wizard_id],
            "doc_model": "vat.report.wizard",
            "docs": self.env["vat.report.wizard"].browse(wizard_id),
            "company_name": company.display_name,
            "currency_name": company.currency_id.name,
            "date_to": data["date_to"],
            "date_from": data["date_from"],
            "based_on": data["based_on"],
            "tax_detail": data["tax_detail"],
            "vat_report": vat_report,
        }

    def _get_ml_fields_vat_report(self):
        return [
            "id",
            "tax_base_amount",
            "balance",
            "tax_line_id",
            "tax_ids",
        ]
