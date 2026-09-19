import io
from collections import defaultdict
from unittest.mock import patch

from markupsafe import Markup

from odoo import Command
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import tagged

from odoo.addons.account.models.chart_template import (
    TEMPLATE_MODELS,
    AccountChartTemplate,
    code_translations,
)
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_CHART_TEMPLATE_LOGGER = "odoo.addons.account.models.chart_template"


def _get_chart_template_mapping(self, get_all=False):
    return {
        "test": {
            "name": "test",
            "country_id": self.env.ref("base.be").id,
            "country_code": None,
            "module": "account",
            "parent": None,
        }
    }


def test_get_data(self, template_code):
    return {
        "template_data": {
            "code_digits": 6,
            "currency_id": self.env.ref("base.EUR").id,
            "property_account_receivable_id": "test_account_receivable_template",
            "property_account_payable_id": "test_account_payable_template",
        },
        "account.tax.group": {
            "tax_group_taxes": {
                "name": "Taxes",
                "sequence": 0,
            },
        },
        "account.journal": self._get_account_journal(template_code),
        "res.company": {
            self.env.company.id: {
                "bank_account_code_prefix": "1000",
                "cash_account_code_prefix": "2000",
                "transfer_account_code_prefix": "3000",
                "income_account_id": "test_account_income_template",
                "expense_account_id": "test_account_expense_template",
                "account_sale_tax_id": "test_tax_1_template",
            },
        },
        "account.account.tag": {
            f"account.account_tax_tag_{i}": {
                "name": f"tax_tag_name_{i}",
                "applicability": "taxes",
                "country_id": "base.be",
            }
            for i in range(1, 9)
        },
        "account.tax": {
            xmlid: _tax_vals(
                name,
                amount,
                "account.account_tax_tag_1",
                fiscal_pos=position,
                alt_taxes=alt,
            )
            for name, xmlid, amount, position, alt in [
                ("Tax 1", "test_tax_1_template", 15, False, False),
                (
                    "Tax 2",
                    "test_tax_2_template",
                    0,
                    "test_fiscal_position_template",
                    "test_tax_1_template",
                ),
            ]
        },
        "account.group": {
            "test_account_group_1": {
                "name": "test_account_group_name_1",
                "code_prefix_start": 222220,
                "code_prefix_end": 222229,
            }
        },
        "account.account": {
            "test_account_receivable_template": {
                "name": "property_receivable_account",
                "code": "411111",
                "account_type": "asset_receivable",
            },
            "test_account_payable_template": {
                "name": "property_payable_account",
                "code": "421111",
                "account_type": "liability_payable",
            },
            "test_account_income_template": {
                "name": "property_income_account",
                "code": "222221",
                "account_type": "income",
                "group_id": "test_account_group_1",
            },
            "test_account_expense_template": {
                "name": "property_expense_account",
                "code": "222222",
                "account_type": "expense",
            },
        },
        "account.fiscal.position": {
            "test_fiscal_position_template": {
                "name": "Fiscal Position",
                "country_id": "base.be",
                "auto_apply": True,
            }
        },
        "account.reconcile.model": {
            "test_account_reconcile_model_1": {
                "name": "test_reconcile_model_with_payment_tolerance",
                "line_ids": [
                    Command.create({"account_id": "test_account_income_template"})
                ],
            }
        },
    }


def _tax_vals(
    name,
    amount,
    tax_tag_id=None,
    children_tax_xmlids=None,
    active=True,
    tax_scope="consu",
    fiscal_pos=False,
    alt_taxes=False,
):
    tag_command = [Command.set([tax_tag_id])] if tax_tag_id else None
    tax_vals = {
        "name": name,
        "amount": amount,
        "amount_type": "percent" if not children_tax_xmlids else "group",
        "tax_group_id": "tax_group_taxes",
        "active": active,
        "tax_scope": tax_scope,
        "fiscal_position_ids": fiscal_pos,
        "original_tax_ids": alt_taxes,
    }
    if children_tax_xmlids:
        tax_vals.update({"children_tax_ids": [Command.set(children_tax_xmlids)]})
    else:
        tax_vals.update(
            {
                "repartition_line_ids": [
                    Command.create(
                        {
                            "document_type": "invoice",
                            "factor_percent": 100,
                            "repartition_type": "base",
                            "tag_ids": tag_command,
                        }
                    ),
                    Command.create(
                        {
                            "document_type": "invoice",
                            "factor_percent": 100,
                            "repartition_type": "tax",
                        }
                    ),
                    Command.create(
                        {
                            "document_type": "refund",
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "document_type": "refund",
                            "factor_percent": 100,
                            "repartition_type": "tax",
                        }
                    ),
                ]
            }
        )
    return tax_vals


def _account_vals(name, code, account_type):
    return {
        "name": name,
        "code": code,
        "account_type": account_type,
    }


CSV_DATA = {
    "tax_1": (
        '"id","name","type_tax_use","amount","amount_type","description","invoice_label","tax_group_id","repartition_line_ids/repartition_type",'
        '"repartition_line_ids/factor_percent","repartition_line_ids/document_type","repartition_line_ids/tag_ids","repartition_line_ids/account_id",'
        '"repartition_line_ids/use_in_tax_closing","description@en"\n'
        '"tax_1","5%","sale","5.0","percent","","VAT 5%","tax_group_taxes","base","","invoice","tax_tag_name_1||tax_tag_name_2","","","Test tax"\n'
        '"","","","","","","","","tax","50","invoice","tax_tag_name_3","test_account_income_template","False",""\n'
        '"","","","","","","","","tax","50","invoice","tax_tag_name_4","test_account_income_template","False",""\n'
        '"","","","","","","","","base","","refund","tax_tag_name_5||tax_tag_name_6","","",""\n'
        '"","","","","","","","","tax","50","refund","tax_tag_name_7","test_account_income_template","False",""\n'
        '"","","","","","","","","tax","50","refund","tax_tag_name_8","test_account_income_template","False",""\n'
    ),
    "tax_4": ('"id","fiscal_position_ids"\n"tax_4","test_fiscal_position_template"\n'),
    "test_fiscal_position_template": (
        '"id","name","country_id","auto_apply"\n'
        '"test_fiscal_position_template","Fiscal Position","base.be","1"\n'
    ),
}


@tagged("post_install", "-at_install")
@patch.object(
    AccountChartTemplate, "_get_chart_template_mapping", _get_chart_template_mapping
)
class TestChartTemplate(AccountTestInvoicingCommon):
    @classmethod
    def _use_chart_template(cls, company, chart_template_ref=None):
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            cls.env["account.chart.template"].try_loading(
                "test", company=company, install_demo=False
            )

    @classmethod
    @AccountTestInvoicingCommon.setup_country("be")
    @patch.object(
        AccountChartTemplate, "_get_chart_template_mapping", _get_chart_template_mapping
    )
    def setUpClass(cls):
        super(AccountTestInvoicingCommon, cls).setUpClass()

        cls.ChartTemplate = cls.env["account.chart.template"].with_company(cls.company)
        cls.country_be = cls.env.ref("base.be")

    def test_parse_csv_integer_field_negative_value(self):
        csv_content = "id,decimal_places\nres_currency_test,-5\n"

        def fake_file_open(path, mode="r"):
            if path.endswith("res.currency.csv"):
                return io.StringIO(csv_content)
            raise FileNotFoundError(path)

        with patch(
            "odoo.addons.account.models.chart_template.file_open", fake_file_open
        ):
            result = self.ChartTemplate._prepare_csv_vals(
                "no_such_template_code", "res.currency", module="account"
            )
        self.assertEqual(result["res_currency_test"]["decimal_places"], -5)

    def test_tax_report_and_manual_tax_tag(self):
        tax_report = self.env["account.report"].create(
            {
                "name": "Tax report 1",
                "country_id": self.country_be.id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "Balance",
                            "expression_label": "balance",
                        }
                    ),
                ],
            }
        )
        self.env["account.report.line"].create(
            {
                "name": "[TAG] Tax report line",
                "report_id": tax_report.id,
                "sequence": max(tax_report.mapped("line_ids.sequence") or [0]) + 1,
                "expression_ids": [
                    Command.create(
                        {
                            "label": "balance",
                            "engine": "tax_tags",
                            "formula": "TAG",
                        }
                    ),
                ],
            }
        )
        tax_report_tag = self.env["account.account.tag"].search(
            [
                ("applicability", "=", "taxes"),
                ("name", "=", "TAG"),
            ]
        )
        self.env["account.account.tag"]._load_records(
            [
                {
                    "xml_id": "account.unsigned_tax_tag",
                    "noupdate": True,
                    "values": {
                        "name": "unsigned tax tag",
                        "applicability": "taxes",
                        "country_id": self.country_be.id,
                    },
                },
            ]
        )
        tax_to_load = {
            "name": "Mixed Tags Tax",
            "amount": 30,
            "amount_type": "percent",
            "tax_group_id": "tax_group_taxes",
            "active": True,
            "repartition_line_ids": [
                Command.create(
                    {
                        "document_type": "invoice",
                        "factor_percent": 100,
                        "repartition_type": "base",
                        "tag_ids": "account.unsigned_tax_tag||TAG",
                    }
                ),
                Command.create(
                    {
                        "document_type": "invoice",
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
                Command.create(
                    {
                        "document_type": "refund",
                        "factor_percent": 100,
                        "repartition_type": "base",
                    }
                ),
                Command.create(
                    {
                        "document_type": "refund",
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
            ],
        }
        self.env["account.chart.template"]._deref_account_tags(
            "test", {"tax1": tax_to_load}
        )
        self.assertEqual(
            tax_to_load["repartition_line_ids"][0],
            Command.create(
                {
                    "document_type": "invoice",
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [
                        Command.set(["account.unsigned_tax_tag", tax_report_tag.id])
                    ],
                }
            ),
        )

    def test_inactive_tag_tax(self):
        inactive_tag = self.env["account.account.tag"].create(
            {
                "name": "Inactive Tax Tag",
                "applicability": "taxes",
                "active": False,
                "country_id": self.country_be.id,
            }
        )
        tax_to_load = {
            "name": "Inactive Tags Tax",
            "amount": 30,
            "amount_type": "percent",
            "tax_group_id": "tax_group_taxes",
            "active": True,
            "repartition_line_ids": [
                Command.create(
                    {
                        "document_type": "invoice",
                        "factor_percent": 100,
                        "repartition_type": "base",
                        "tag_ids": inactive_tag.name,
                    }
                ),
            ],
        }
        self.env["account.chart.template"]._deref_account_tags(
            "test", {"tax1": tax_to_load}
        )
        self.assertEqual(
            tax_to_load["repartition_line_ids"][0],
            Command.create(
                {
                    "document_type": "invoice",
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [(Command.set([inactive_tag.id]))],
                }
            ),
        )

    def test_update_taxes_creation(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.tax"].update(
                {
                    xmlid: _tax_vals(name, amount, fiscal_pos=position, alt_taxes=alt)
                    for name, xmlid, amount, position, alt in [
                        ("Tax 3", "test_tax_3_template", 16, False, False),
                        (
                            "Tax 4",
                            "test_tax_4_template",
                            17,
                            "test_fiscal_position_template",
                            "test_tax_2_template",
                        ),
                    ]
                }
            )
            data["account.tax"]["test_tax_1_template"]["fiscal_position_ids"] = (
                "test_fiscal_position_template"
            )
            data["account.tax"]["test_tax_1_template"]["original_tax_ids"] = (
                "test_tax_3_template"
            )
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False, force_create=False
            )

        self.assertFalse(
            self.env["account.chart.template"].ref(
                "test_tax_3_template", raise_if_not_found=False
            )
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        tax_1, tax_2, tax_3, tax_4 = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id])]
        )
        self.assertRecordValues(
            tax_1 | tax_2 | tax_3 | tax_4,
            [
                {"name": "Tax 1"},
                {"name": "Tax 2"},
                {"name": "Tax 3"},
                {"name": "Tax 4"},
            ],
        )

        fiscal_position = self.env["account.fiscal.position"].search([])

        self.assertEqual(fiscal_position.map_tax(tax_1), tax_2)
        self.assertEqual(fiscal_position.map_tax(tax_2), tax_4)
        self.assertEqual(fiscal_position.map_tax(tax_3), tax_1)

    def test_update_accounts_creation(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.account"].update(
                {
                    xmlid: _account_vals(name, code, account_type)
                    for name, xmlid, code, account_type in [
                        (
                            "Account 3",
                            "test_account_3_template",
                            "333333",
                            "asset_current",
                        ),
                        (
                            "Account 4",
                            "test_account_4_template",
                            "444444",
                            "asset_current",
                        ),
                    ]
                }
            )
            data["account.fiscal.position"]["test_fiscal_position_template"][
                "account_ids"
            ] = [
                Command.create(
                    {
                        "account_src_id": "test_account_3_template",
                        "account_dest_id": "test_account_4_template",
                    }
                ),
            ]
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False, force_create=False
            )

        self.assertFalse(
            self.env["account.chart.template"].ref(
                "test_account_3_template", raise_if_not_found=False
            )
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        fiscal_position = self.env["account.fiscal.position"].search([])
        self.assertEqual(
            fiscal_position.map_account(
                self.env["account.chart.template"].ref("test_account_3_template")
            ),
            self.env["account.chart.template"].ref("test_account_4_template"),
        )

    def test_remove_fiscal_position_try_loading_force_create_false(self):
        fiscal_position = self.env["account.fiscal.position"].search(
            [
                ("name", "=", "Fiscal Position"),
            ]
        )
        self.assertTrue(fiscal_position, "Fiscal Position should exist before deletion")

        fiscal_position.unlink()

        self.assertFalse(fiscal_position.exists(), "Fiscal Position should be deleted")

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False, force_create=False
            )

        fiscal_position_after_reload = self.env["account.fiscal.position"].search(
            [
                ("name", "=", "Fiscal Position"),
            ]
        )
        self.assertFalse(
            fiscal_position_after_reload,
            "Fiscal Position should not be recreated when force_create=False",
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False, force_create=True
            )

        fiscal_position_after_reload = self.env["account.fiscal.position"].search(
            [
                ("name", "=", "Fiscal Position"),
            ]
        )
        self.assertTrue(
            fiscal_position_after_reload,
            "Fiscal Position should be recreated when force_create=True",
        )

    def test_new_tax_rate(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            del data["account.tax"]["test_tax_1_template"]
            data["account.tax"]["test_tax_3_template"] = _tax_vals("Tax 3", 30)
            data["account.tax"]["test_tax_2_template"]["original_tax_ids"] = (
                "test_tax_3_template"
            )
            data["res.company"][self.env.company.id]["account_sale_tax_id"] = (
                "test_tax_3_template"
            )
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        taxes = self.env["account.tax"].search(
            [("company_ids", "in", self.company.ids)]
        )
        self.assertRecordValues(
            taxes,
            [
                {"name": "Tax 1"},
                {"name": "Tax 2"},
                {"name": "Tax 3"},
            ],
        )

        tax_1, tax_2, tax_3 = taxes
        fiscal_position = self.env["account.fiscal.position"].search(
            [("company_id", "=", self.company.id)]
        )

        self.assertEqual(fiscal_position.map_tax(tax_1), tax_2)
        self.assertEqual(fiscal_position.map_tax(tax_3), tax_2)

        new_company = self.env["res.company"].create({"name": "New Company"})
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=new_company, install_demo=False
            )

        taxes = self.env["account.tax"].search([("company_ids", "in", new_company.ids)])
        self.assertRecordValues(
            taxes,
            [
                {"name": "Tax 2"},
                {"name": "Tax 3"},
            ],
        )

        tax_2, tax_3 = taxes
        fiscal_position = self.env["account.fiscal.position"].search(
            [("company_id", "=", new_company.id)]
        )
        self.assertEqual(fiscal_position.map_tax(tax_3), tax_2)
        self.assertEqual(new_company.account_config_id.account_sale_tax_id, tax_3)

    def test_update_taxes_update(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.account.tag"]["account.account_tax_tag_1"]["name"] += " [DUP]"
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        updated_tax = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "like", "%Tax 1")]
        )
        self.assertEqual(len(updated_tax), 1)
        self.assertEqual(
            updated_tax.invoice_repartition_line_ids.tag_ids.name,
            "tax_tag_name_1 [DUP]",
        )

    def test_update_taxes_update_rounding(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.account.tag"]["account.account_tax_tag_1"]["name"] += " [DUP]"
            data["account.tax"]["test_tax_1_template"]["amount"] += 0.00001
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        updated_tax = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "like", "%Tax 1")]
        )
        self.assertEqual(len(updated_tax), 1)
        self.assertEqual(
            updated_tax.invoice_repartition_line_ids.tag_ids.name,
            "tax_tag_name_1 [DUP]",
        )

    def test_update_taxes_recreation(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.tax"]["test_tax_1_template"]["name"] = "Tax 1 modified"
            data["account.tax"]["test_tax_1_template"]["amount"] += 1
            return data

        tax_existing = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "Tax 1")]
        )
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        self.assertRecordValues(tax_existing, [{"name": "[old] Tax 1", "amount": 15}])

        new_tax = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "Tax 1 modified")]
        )
        self.assertEqual(new_tax.amount, tax_existing.amount + 1)

    def test_update_taxes_removed_from_templates(self):
        fiscal_position = self.env["account.fiscal.position"].search([])
        self.env["account.tax"].search(
            [("company_ids", "in", self.company.ids)]
        ).unlink()

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        self.assertEqual(
            len(
                self.env["account.tax"].search(
                    [("company_ids", "in", self.company.ids)]
                )
            ),
            2,
        )
        self.assertEqual(len(fiscal_position.tax_ids.original_tax_ids), 1)

        fiscal_position.tax_ids.original_tax_ids = False
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        self.assertEqual(len(fiscal_position.tax_ids.original_tax_ids), 0)

    def test_update_taxes_conflict_name(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.tax"]["test_tax_1_template"]["amount"] = 40
            return data

        def local_get_data2(self, template_code):
            data = test_get_data(self, template_code)
            data["account.tax"]["test_tax_1_template"]["amount"] = 15
            return data

        tax_1_existing = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "Tax 1")]
        )
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )
        tax_1_old = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "[old] Tax 1")]
        )
        tax_1_new = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "Tax 1")]
        )
        self.assertEqual(
            tax_1_old, tax_1_existing, "Old tax still exists but with a different name."
        )
        self.assertEqual(
            len(tax_1_new), 1, "New tax have been created with the original name."
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data2,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )
        tax_1_old_first = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "[old] Tax 1")]
        )
        tax_1_old_second = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "[old1] Tax 1")]
        )
        tax_1_latest = self.env["account.tax"].search(
            [("company_ids", "in", [self.company.id]), ("name", "=", "Tax 1")]
        )

        self.assertEqual(
            tax_1_old, tax_1_old_first, "Old renamed tax is still the same."
        )
        self.assertEqual(tax_1_old_second, tax_1_new, "Outdated tax is renamed again.")
        self.assertEqual(
            len(tax_1_latest), 1, "New tax have been created with the original name."
        )

    def test_update_taxes_multi_company(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.tax"]["test_tax_1_template"]["amount"] += 1
            return data

        company_2 = self.env["res.company"].create(
            {
                "name": "TestCompany2",
                "country_id": self.env.ref("base.be").id,
            }
        )
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=company_2, install_demo=False
            )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )
            self.env["account.chart.template"].try_loading(
                "test", company=company_2, install_demo=False
            )

        taxes_1_companies = self.env["account.tax"].search(
            [
                ("name", "=like", "%Tax 1"),
                ("company_ids", "in", [self.company.id, company_2.id]),
            ]
        )
        self.assertEqual(len(taxes_1_companies), 4)

    def test_update_account_codes_conflict(self):
        standard_account = self.env["account.chart.template"].ref(
            "test_account_income_template"
        )
        standard_account.code = "111111"

        problematic_account = self.env["account.account"].create(
            {
                "code": "222221",
                "name": "problematic_account",
            }
        )

        self.env["ir.model.data"].search(
            [
                ("name", "=", f"{self.company.id}_test_account_expense_template"),
                ("module", "=", "account"),
            ]
        ).unlink()

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        xmlid_account = self.env.ref(
            f"account.{self.company.id}_test_account_income_template"
        )
        self.assertEqual(
            problematic_account,
            xmlid_account,
            "xmlid is not pointing to the right account",
        )

    def test_update_taxes_children_tax_ids(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            normal_tax_xmlids = ["test_tax_3_template", "test_tax_4_template"]
            data["account.tax"].update(
                {
                    xmlid: _tax_vals(
                        name, amount, children_tax_xmlids=children_tax_xmlids
                    )
                    for name, xmlid, amount, children_tax_xmlids in [
                        ("Tax 3", normal_tax_xmlids[0], 16, None),
                        ("Tax 4", normal_tax_xmlids[1], 17, None),
                        (
                            "Tax with children",
                            "test_tax_5_group_template",
                            0,
                            normal_tax_xmlids,
                        ),
                    ]
                }
            )
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        parent_tax = self.env["account.tax"].search(
            [
                ("company_ids", "in", [self.company.id]),
                ("name", "=", "Tax with children"),
            ]
        )
        children_taxes = self.env["account.tax"].search(
            [
                ("company_ids", "in", [self.company.id]),
                ("name", "in", ["Tax 3", "Tax 4"]),
            ]
        )
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been created.")
        self.assertEqual(
            len(children_taxes), 2, "Two children should have been created."
        )
        self.assertEqual(
            parent_tax.children_tax_ids.ids,
            children_taxes.ids,
            "The parent and its children taxes should be linked together.",
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        self.assertEqual(
            parent_tax.name,
            "Tax with children",
            "The parent tax created before should not have changed",
        )

    def test_update_taxes_children_tax_ids_inactive(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            normal_tax_xmlids = ["test_tax_3_template", "test_tax_4_template"]
            data["account.tax"].update(
                {
                    xmlid: _tax_vals(
                        name,
                        amount,
                        children_tax_xmlids=children_tax_xmlids,
                        active=active,
                    )
                    for name, xmlid, amount, children_tax_xmlids, active in [
                        ("Inactive Tax 3", normal_tax_xmlids[0], 16, None, False),
                        ("Inactive Tax 4", normal_tax_xmlids[1], 17, None, False),
                        (
                            "Inactive Tax with children",
                            "test_tax_5_group_template",
                            0,
                            normal_tax_xmlids,
                            False,
                        ),
                    ]
                }
            )
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        parent_tax = (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_ids", "in", [self.company.id]),
                    ("name", "=", "Inactive Tax with children"),
                ]
            )
        )
        children_taxes = (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_ids", "in", [self.company.id]),
                    ("name", "in", ["Inactive Tax 3", "Inactive Tax 4"]),
                ]
            )
        )
        self.assertEqual(
            len(parent_tax),
            1,
            "The parent tax should have been created, even if it is inactive.",
        )
        self.assertFalse(parent_tax.active, "The parent tax should be inactive.")
        self.assertEqual(
            len(children_taxes),
            2,
            "Two children should have been created, even if they are inactive.",
        )
        self.assertEqual(
            children_taxes.mapped("active"),
            [False] * 2,
            "Children taxes should be inactive.",
        )

    def test_update_reload_no_new_data(self):
        def get_domain(model):
            if model == "account.account.tag":
                return [("country_id", "=", self.company.country_id.id)]
            elif model in (
                "account.account",
                "account.tax.group",
                "account.tax",
                "account.tax.repartition.line",
            ):
                return [("company_ids", "=", self.company.id)]
            else:
                return [("company_id", "=", self.company.id)]

        sub_models = ("account.tax.repartition.line", "account.account.tag")
        data_before = {}
        for model in TEMPLATE_MODELS + sub_models:
            data_before[model] = self.env[model].search(get_domain(model))

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        for model in TEMPLATE_MODELS + sub_models:
            data_after = self.env[model].search(get_domain(model))
            self.assertEqual(data_before[model], data_after)

    def test_first_load_of_a_preset_template_sets_the_company_defaults(self):
        company = self.env["res.company"].create(
            {"name": "Preset Co", "country_id": self.country_be.id}
        )
        company.account_config_id.chart_template = "test"
        self._use_chart_template(company)

        ChartTemplate = self.env["account.chart.template"].with_company(company)
        receivable = self.env["ir.default"]._get(
            "res.partner", "property_account_receivable_id", company_id=company.id
        )
        payable = self.env["ir.default"]._get(
            "res.partner", "property_account_payable_id", company_id=company.id
        )
        self.assertEqual(
            receivable, ChartTemplate.ref("test_account_receivable_template").id
        )
        self.assertEqual(payable, ChartTemplate.ref("test_account_payable_template").id)
        self.assertEqual(
            company.account_config_id.income_account_id,
            ChartTemplate.ref("test_account_income_template"),
        )

    def test_reload_keeps_the_company_defaults_already_set(self):
        other_receivable = self.env["account.account"].create(
            {
                "name": "Chosen receivable",
                "code": "411999",
                "account_type": "asset_receivable",
                "company_ids": [Command.set(self.company.ids)],
            }
        )
        self.env["ir.default"].set(
            "res.partner",
            "property_account_receivable_id",
            other_receivable.id,
            company_id=self.company.id,
        )
        income_before = self.company.account_config_id.income_account_id

        self._use_chart_template(self.company)

        self.assertEqual(
            self.env["ir.default"]._get(
                "res.partner",
                "property_account_receivable_id",
                company_id=self.company.id,
            ),
            other_receivable.id,
        )
        self.assertEqual(
            self.company.account_config_id.income_account_id, income_before
        )

    def test_unknown_company_fields(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["res.company"][company.id]["unknown_company_key"] = (
                "unknown_company_value"
            )
            return data

        company = self.company
        company.account_config_id.chart_template = False

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            with self.assertRaisesRegex(ValueError, "unknown_company_key"):
                self.env["account.chart.template"].with_context(
                    l10n_check_fields_complete=True
                ).try_loading("test", company=company, install_demo=False)

            self.env["account.chart.template"].try_loading(
                "test", company=company, install_demo=False
            )

    def test_branch(self):
        company = self.env["res.company"].create([{"name": "Test Company"}])
        branch = self.env["res.company"].create(
            [
                {
                    "name": "Test Branch",
                    "parent_id": company.id,
                }
            ]
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=company, install_demo=True
            )
        self.assertEqual(company.account_config_id.chart_template, "test")
        self.assertEqual(branch.account_config_id.chart_template, "test")

    def test_change_coa(self):
        def _get_chart_template_mapping(self, get_all=False):
            return {
                "other_test": {
                    "name": "test",
                    "country_id": None,
                    "country_code": None,
                    "module": "account",
                    "parent": None,
                }
            }

        self.company.account_config_id.anglo_saxon_accounting = True

        with (
            patch.object(
                AccountChartTemplate,
                "_get_chart_template_mapping",
                _get_chart_template_mapping,
            ),
            patch.object(
                AccountChartTemplate,
                "_prepare_chart_template_data",
                side_effect=test_get_data,
                autospec=True,
            ),
        ):
            self.env["account.chart.template"].try_loading(
                "other_test", company=self.company, install_demo=True
            )

            branch, other_company = self.env["res.company"].create(
                [
                    {
                        "name": "Test Branch",
                        "parent_id": self.company.id,
                    },
                    {
                        "name": "Other Test Company",
                    },
                ]
            )
            self.env.cr.precommit.run()

        self.assertEqual(self.company.account_config_id.chart_template, "other_test")
        self.assertEqual(branch.account_config_id.chart_template, "other_test")
        self.assertFalse(self.company.account_config_id.anglo_saxon_accounting)

        shared_account = self.env["account.account"].create(
            [
                {
                    "name": "Shared Account",
                    "company_ids": [
                        Command.set((self.company | branch | other_company).ids)
                    ],
                    "code_mapping_ids": [
                        Command.create(
                            {"company_id": self.company.id, "code": "180001"}
                        ),
                        Command.create({"company_id": branch.id, "code": "180001"}),
                        Command.create(
                            {"company_id": other_company.id, "code": "180001"}
                        ),
                    ],
                }
            ]
        )

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=True
            )
        self.assertEqual(self.company.account_config_id.chart_template, "test")
        self.assertEqual(branch.account_config_id.chart_template, "test")

        self.assertEqual(shared_account.company_ids, other_company)

    def test_update_tax_with_non_existent_tag(self):
        tax_to_load = {
            "name": "Mixed Tags Tax",
            "amount": 30,
            "amount_type": "percent",
            "tax_group_id": "tax_group_taxes",
            "active": True,
            "repartition_line_ids": [
                Command.create(
                    {
                        "document_type": "invoice",
                        "factor_percent": 100,
                        "repartition_type": "base",
                        "tag_ids": "+TAG",
                    }
                ),
                Command.create(
                    {
                        "document_type": "invoice",
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
                Command.create(
                    {
                        "document_type": "refund",
                        "factor_percent": 100,
                        "repartition_type": "base",
                    }
                ),
                Command.create(
                    {
                        "document_type": "refund",
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
            ],
        }
        with self.assertRaisesRegex(RedirectWarning, "update your localization"):
            self.env["account.chart.template"]._deref_account_tags(
                "test", {"tax1": tax_to_load}
            )

    def test_install_with_translations(self):
        def local_get_mapping(self, get_all=False):
            return {
                "translation": {
                    "name": "translation",
                    "country_id": None,
                    "country_code": None,
                    "modules": ["account"],
                    "parent": None,
                }
            }

        company = self.company

        non_chart_data = {
            "account.group": {
                "no_translation.test_chart_template_company_test_free_account_group": {
                    "name": "Free Account Group",
                    "code_prefix_start": 333330,
                    "code_prefix_end": 333339,
                    "company_id": company.id,
                },
            },
            "account.account": {
                "translation.test_chart_template_company_test_free_account": {
                    "name": "Free Account",
                    "code": "333331",
                    "account_type": "asset_current",
                    "company_ids": [Command.link(company.id)],
                },
            },
            "account.tax": {
                "translation.test_chart_template_company_test_free_tax": {
                    "name": "Free Tax",
                    "description": "Free Tax Description",
                    "amount": "0.00",
                    "company_ids": [Command.link(company.id)],
                },
            },
        }

        def test_post_load_data(template_code, company, template_data):
            for model, data in non_chart_data.items():
                for xml_id, values in data.items():
                    self.env[model]._load_records(
                        [
                            {
                                "xml_id": xml_id,
                                "values": values,
                            }
                        ]
                    )

        translation_update_for_test_get_data = {
            "account.journal": {
                "bank": {
                    "name": "Bank",
                    "code": "B",
                    "__translation_module__": {
                        "name": "translation",
                        "code": "translation",
                    },
                },
            },
            "account.tax": {
                "test_tax_1_template": {
                    "name": "Tax 1",
                    "description": "Tax 1 Description",
                    "__translation_module__": {
                        "name": "translation",
                        "description": "translation2",
                    },
                },
            },
            "account.tax.group": {
                "tax_group_taxes": {
                    "name": "Taxes",
                    "name@fr": "Taxes FR",
                    "__translation_module__": {
                        "name": "translation",
                    },
                },
            },
        }

        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            for model, record_info in translation_update_for_test_get_data.items():
                for xmlid, data_update in record_info.items():
                    data[model][xmlid].update(data_update)
            return data

        company.partner_id.lang = self.env["res.lang"]._activate_lang("fr_BE").code

        mock_python_translations = {}

        for module, lang, value, translation in [
            (
                "translation",
                "fr",
                "Taxes",
                "WRONG",
            ),
            (
                "translation",
                "fr",
                "Free Account",
                "Free Account FR",
            ),
            ("translation", "fr", "Bank", "Bank FR"),
            ("translation", "fr", "B", "B FR"),
            ("translation", "fr", "Tax 1", "Tax 1 FR"),
            ("translation", "fr_BE", "Free Account", "Free Account FR_BE"),
            ("translation", "fr", "Free Tax", "Free Tax FR"),
            ("translation", "fr", "Free Tax Description", "Free Tax Description FR"),
            (
                "translation2",
                "fr",
                "Tax 1 Description",
                "Tax 1 Description translation2/FR",
            ),
            ("account", "fr", "Free Account Group", "Free Account Group account/FR"),
        ]:
            mock_python_translations.setdefault((module, lang), {})[value] = translation

        with patch.object(
            AccountChartTemplate,
            "_get_chart_template_mapping",
            side_effect=local_get_mapping,
            autospec=True,
        ):
            with patch.object(
                AccountChartTemplate,
                "_prepare_chart_template_data",
                side_effect=local_get_data,
                autospec=True,
            ):
                with patch.object(
                    AccountChartTemplate, "_post_load_data", wraps=test_post_load_data
                ):
                    with patch.object(
                        code_translations,
                        "python_translations",
                        mock_python_translations,
                    ):
                        self.env["account.chart.template"].try_loading(
                            "translation", company=company, install_demo=False
                        )

        translatable_model_fields = self.env[
            "account.chart.template"
        ]._get_fields_translatable_template_model()
        untranslatable_model_fields = self.env[
            "account.chart.template"
        ]._get_untranslatable_fields_to_translate()
        fields_to_translate = {
            model: set(
                translatable_model_fields.get(model, [])
                + untranslatable_model_fields.get(model, [])
            )
            for model in TEMPLATE_MODELS
        }

        self.assertEqual(
            {
                f"{xmlid}.{field}@{lang}": self.env["account.chart.template"]
                .ref(xmlid)
                .with_context(lang=lang)[field]
                for chart_like_data in [
                    non_chart_data,
                    translation_update_for_test_get_data,
                ]
                for model, data in chart_like_data.items()
                for xmlid, record_data in data.items()
                for field in record_data
                if field in fields_to_translate.get(model, set())
                for lang in ["en_US", "fr_BE"]
            },
            {
                "bank.code@en_US": "B FR",
                "bank.code@fr_BE": "B FR",
                "bank.name@en_US": "Bank",
                "bank.name@fr_BE": "Bank FR",
                "no_translation.test_chart_template_company_test_free_account_group.name@en_US": "Free Account Group",
                "no_translation.test_chart_template_company_test_free_account_group.name@fr_BE": "Free Account Group account/FR",
                "tax_group_taxes.name@en_US": "Taxes",
                "tax_group_taxes.name@fr_BE": "Taxes FR",
                "test_tax_1_template.description@en_US": Markup(
                    "<div>Tax 1 Description</div>"
                ),
                "test_tax_1_template.description@fr_BE": Markup(
                    "Tax 1 Description translation2/FR"
                ),
                "test_tax_1_template.name@en_US": "Tax 1",
                "test_tax_1_template.name@fr_BE": "Tax 1 FR",
                "translation.test_chart_template_company_test_free_account.name@en_US": "Free Account",
                "translation.test_chart_template_company_test_free_account.name@fr_BE": "Free Account FR_BE",
                "translation.test_chart_template_company_test_free_tax.description@en_US": Markup(
                    "<div>Free Tax Description</div>"
                ),
                "translation.test_chart_template_company_test_free_tax.description@fr_BE": Markup(
                    "<div>Free Tax Description FR</div>"
                ),
                "translation.test_chart_template_company_test_free_tax.name@en_US": "Free Tax",
                "translation.test_chart_template_company_test_free_tax.name@fr_BE": "Free Tax FR",
            },
        )

    def test_parsed_csv_submodel_being_loaded(self):
        def get_rep_line_data(x):
            return (
                x.document_type,
                x.repartition_type,
                x.factor_percent,
                x.use_in_tax_closing,
            )

        with patch(
            "odoo.addons.account.models.chart_template.file_open",
            side_effect=lambda *args: io.StringIO(CSV_DATA["tax_1"]),
        ):
            data = {"account.tax": self.ChartTemplate._get_account_tax("test")}
        self.ChartTemplate._load_data(data)

        tax_1 = self.env.ref(
            f"account.{self.company.id}_tax_1", raise_if_not_found=False
        )
        tax_rep_lines = tax_1.repartition_line_ids.filtered(
            lambda x: x.repartition_type == "tax"
        )
        self.assertEqual(
            [
                ("invoice", "tax", 50.0, False),
                ("invoice", "tax", 50.0, False),
                ("refund", "tax", 50.0, False),
                ("refund", "tax", 50.0, False),
            ],
            tax_rep_lines.mapped(get_rep_line_data),
        )

    def test_parsed_csv_submodel_being_updated(self):
        def local_get_data(self, template_code):
            return {
                **test_get_data(self, template_code),
                "account.tax": {
                    xmlid: _tax_vals(name, amount)
                    for name, xmlid, amount in [
                        ("Tax 1", "test_tax_1_template", 15),
                        ("Tax 2", "test_tax_2_template", 0),
                        ("Tax 3", "test_tax_3_template", 16),
                        ("Tax 4", "test_tax_4_template", 17),
                    ]
                },
            }

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        with patch(
            "odoo.addons.account.models.chart_template.file_open",
            side_effect=lambda *args: io.StringIO(
                CSV_DATA["test_fiscal_position_template"]
            ),
        ):
            data = {
                "account.fiscal.position": self.ChartTemplate._get_account_fiscal_position(
                    "test"
                )
            }
        self.ChartTemplate._pre_reload_data(self.company, {}, data)
        self.ChartTemplate._load_data(data)

    def test_command_int_values(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data["account.account"].update(
                {
                    "test_account": {
                        "name": "Test account A",
                        "code": "777777",
                        "account_type": "income_other",
                        "tag_ids": [
                            (6, 0, self.ref("account.account_tag_investing").ids)
                        ],
                    },
                    "test_account_2": {
                        "name": "Test account B",
                        "code": "777778",
                        "account_type": "income_other",
                        "tag_ids": [
                            (5, 0, 0),
                            (
                                0,
                                0,
                                {
                                    "name": "Test account tag",
                                    "applicability": "accounts",
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "name": "Test account tag 2",
                                    "applicability": "accounts",
                                },
                            ),
                        ],
                    },
                }
            )
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=self.company, install_demo=False
            )

        accounts = self.env["account.account"].search(
            [
                ("company_ids", "=", self.company.id),
                ("code", "in", ("777777", "777778")),
            ],
            order="code asc",
        )
        self.assertEqual(2, len(accounts))
        self.assertEqual(
            self.env.ref("account.account_tag_investing"), accounts[0].tag_ids
        )
        self.assertEqual(
            {"Test account tag", "Test account tag 2"},
            set(accounts[1].tag_ids.mapped("name")),
        )

    def test_chart_template_company_without_country(self):
        company = self.env["res.company"].create(
            {"name": "Test Company Without country"}
        )
        self.assertFalse(company.country_id)
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=company, install_demo=False
            )
        self.assertEqual(company.country_id.code, "BE")

    def test_bank_account_code_prefix(self):
        company = self.env["res.company"].create(
            {"name": "Test Company Without Bank Prefix"}
        )

        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            del data["res.company"][company.id]["bank_account_code_prefix"]
            return data

        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=local_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=company, install_demo=False
            )
        self.assertEqual(company.account_config_id.chart_template, "test")

    def test_tax_exigibility_is_scoped_to_the_loading_company(self):
        transition_account = self.env["account.account"].create(
            {
                "name": "CABA transition",
                "code": "998877",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(self.company.id)],
            }
        )
        self.env["account.tax"].with_company(self.company).create(
            {
                "name": "Some other company's cash basis tax",
                "amount": 10,
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": transition_account.id,
                "company_ids": [Command.set(self.company.ids)],
            }
        )
        self.env.flush_all()

        other_company = self.env["res.company"].create({"name": "Untainted Co"})
        self.assertFalse(other_company.account_config_id.tax_exigibility)
        with patch.object(
            AccountChartTemplate,
            "_prepare_chart_template_data",
            side_effect=test_get_data,
            autospec=True,
        ):
            self.env["account.chart.template"].try_loading(
                "test", company=other_company, install_demo=False
            )

        self.assertFalse(
            self.env["account.tax"].search_count(
                [
                    *self.env["account.tax"]._check_company_domain(other_company),
                    ("tax_exigibility", "=", "on_payment"),
                ]
            ),
            "precondition: the loaded company owns no cash-basis tax",
        )
        self.assertFalse(
            other_company.account_config_id.tax_exigibility,
            "cash basis must not be enabled for a company that owns no caba tax",
        )

    def test_model_data_skips_a_template_function_returning_none(self):
        def contributes_nothing(self, template_code):
            return None

        contributes_nothing._l10n_template = (None, "account.account")
        contributes_nothing._module = "account"

        register = self.ChartTemplate._template_register
        register[None]["account.account"].append(contributes_nothing)
        try:
            data = self.ChartTemplate._prepare_chart_template_model_data(
                "test", "account.account"
            )
        finally:
            register[None]["account.account"].remove(contributes_nothing)
        self.assertIsInstance(data, dict)

    def test_parse_csv_unknown_submodel_column_is_ignored(self):
        csv_content = (
            "id,name,amount,repartition_line_ids/repartition_type,"
            "repartition_line_ids/no_such_field\n"
            "csv_tax,A tax,10,tax,42\n"
        )

        def fake_file_open(path, mode="r"):
            if path.endswith("account.tax.csv"):
                return io.StringIO(csv_content)
            raise FileNotFoundError(path)

        with (
            patch(
                "odoo.addons.account.models.chart_template.file_open", fake_file_open
            ),
            self.assertLogs(_CHART_TEMPLATE_LOGGER, "WARNING") as logs,
        ):
            result = self.ChartTemplate._prepare_csv_vals(
                "no_such_template_code", "account.tax", module="account"
            )
        self.assertEqual(len(logs.output), 1)
        self.assertIn(
            "ignoring column 'repartition_line_ids/no_such_field'", logs.output[0]
        )
        self.assertEqual(result["csv_tax"]["name"], "A tax")
        repartition = result["csv_tax"]["repartition_line_ids"]
        self.assertEqual(repartition[0][2], {"repartition_type": "tax"})

    def test_parse_csv_leading_row_without_id_is_reported(self):
        csv_content = (
            "id,name,amount,repartition_line_ids/repartition_type\n"
            ",,,base\n"
            "csv_tax,A tax,10,tax\n"
        )

        def fake_file_open(path, mode="r"):
            if path.endswith("account.tax.csv"):
                return io.StringIO(csv_content)
            raise FileNotFoundError(path)

        with patch(
            "odoo.addons.account.models.chart_template.file_open", fake_file_open
        ):
            with self.assertRaisesRegex(ValueError, r"account\.tax\.csv, line 2"):
                self.ChartTemplate._prepare_csv_vals(
                    "no_such_template_code", "account.tax", module="account"
                )

    def test_utility_account_codes_all_follow_code_digits(self):
        for code_digits in (4, 6, 9, 12):
            with self.subTest(code_digits=code_digits):
                values = self.ChartTemplate._prepare_utility_account_vals(
                    self.company, {"code_digits": code_digits}
                )
                explicit_codes = {
                    fname: vals["code"]
                    for fname, vals in values.items()
                    if vals.get("code")
                }
                self.assertTrue(explicit_codes)
                for fname, code in explicit_codes.items():
                    self.assertEqual(
                        len(code),
                        code_digits,
                        f"{fname} is {len(code)} characters in a "
                        f"{code_digits}-digit chart",
                    )
        self.assertEqual(
            self.ChartTemplate._prepare_utility_account_vals(
                self.company, {"code_digits": 6}
            )["account_journal_early_pay_discount_loss_account_id"]["code"],
            "999998",
            "six-digit charts must keep the historical code",
        )

    def test_base_template_cannot_be_installed_directly(self):
        def mapping(self, get_all=False):
            base = {
                "name": "Base template",
                "country_id": self.env.ref("base.be").id,
                "country_code": None,
                "module": "account",
                "parent": None,
                "visible": False,
            }
            return {"base_only": base} if get_all else {}

        company = self.env["res.company"].create({"name": "Guarded Co"})
        with patch.object(AccountChartTemplate, "_get_chart_template_mapping", mapping):
            with self.assertRaisesRegex(UserError, "shouldn't be selected directly"):
                self.env["account.chart.template"].try_loading(
                    "base_only", company=company, install_demo=False
                )

    def test_template_company_field_matches_each_model(self):
        for model in TEMPLATE_MODELS + ("account.move",):
            with self.subTest(model=model):
                fname = self.ChartTemplate._template_company_field(model)
                self.assertIn(fname, self.env[model]._fields)
        self.assertEqual(
            self.ChartTemplate._template_company_field("account.account"),
            "company_ids",
            "account.account is the one TEMPLATE_MODEL that carries company_ids",
        )

    def test_parse_csv_resolve_comodel_walks_relations_only(self):
        Tax = self.env["account.tax"]
        self.assertEqual(
            self.ChartTemplate._resolve_csv_comodel(
                Tax, ["repartition_line_ids"]
            )._name,
            "account.tax.repartition.line",
        )
        self.assertIsNone(
            self.ChartTemplate._resolve_csv_comodel(Tax, ["name"]),
            "a non-relational field names no sub-record",
        )
        self.assertIsNone(
            self.ChartTemplate._resolve_csv_comodel(Tax, ["no_such_field"]),
            "an unknown field names no sub-record",
        )

    def test_load_should_delay_defers_only_uncreated_models(self):
        should_delay = self.ChartTemplate._load_should_delay
        self.assertTrue(
            should_delay(
                set(), ["account.account"], "account.tax", "invoice_label", "x"
            )
            is False,
            "a non-relational field is never delayed",
        )
        self.assertTrue(
            should_delay(
                set(), ["account.tax.group"], "account.tax", "tax_group_id", "grp"
            ),
            "a relation to a model still pending is delayed",
        )
        self.assertFalse(
            should_delay(
                {"account.tax.group"}, [], "account.tax", "tax_group_id", "grp"
            ),
            "a relation to a model already created is not delayed",
        )
        self.assertFalse(
            should_delay(
                set(), ["account.tax.group"], "account.tax", "tax_group_id", 7
            ),
            "an integer is already a database id",
        )

    def test_auto_install_skips_invisible_templates(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "account")], limit=1
        )
        company = self.env.company
        base = {"country_id": company.country_id.id, "visible": False}
        selectable = {"country_id": company.country_id.id, "visible": True}

        with patch.object(
            type(module),
            "account_templates",
            {"a_base": base, "a_selectable": selectable},
        ):
            self.assertEqual(
                module._account_template_to_auto_install(),
                "a_selectable",
                "the invisible base must be skipped even though it comes first",
            )
        with patch.object(type(module), "account_templates", {"a_base": base}):
            self.assertIsNone(
                module._account_template_to_auto_install(),
                "a module offering only base templates auto-installs nothing",
            )

    def test_reload_xmlid_mapping_keeps_the_batch_prefetchable(self):
        accounts = self.ChartTemplate._reload_existing_records(
            self.company, "account.account"
        )
        self.assertGreater(
            len(accounts), 1, "the fixture must hold more than one account"
        )
        mapping = self.ChartTemplate._reload_xmlid_mapping(accounts)
        self.assertTrue(mapping, "the company's accounts must carry account.* xmlids")

        for record in mapping.values():
            self.assertEqual(len(record), 1, "each entry addresses exactly one record")
            self.assertGreater(
                len(list(record._prefetch_ids)),
                1,
                "a mapped record must keep the whole batch prefetchable; browsing it "
                "alone turns every later field read into its own query",
            )

        self.env.invalidate_all()
        before = self.cr.sql_statement_count
        for record in mapping.values():
            record.code
            record.account_type
        queries = self.cr.sql_statement_count - before
        self.assertLess(
            queries,
            len(mapping),
            "reading two fields across the mapping must batch, not cost a query per "
            "record; %d records took %d queries" % (len(mapping), queries),
        )

    def test_guess_chart_template_falls_back_to_the_generic_chart(self):
        mapping = {
            "zz_first": {
                "name": "First by module order",
                "country_id": self.country_be.id,
                "module": "account",
                "parent": None,
            },
            "generic_coa": {
                "name": "Generic",
                "country_id": False,
                "module": "account",
                "parent": None,
            },
        }
        country_without_template = self.env.ref("base.af")
        with patch.object(
            AccountChartTemplate,
            "_get_chart_template_mapping",
            lambda self, get_all=False: mapping,
        ):
            self.assertEqual(
                self.ChartTemplate._guess_chart_template(country_without_template),
                "generic_coa",
                "a country no template declares must fall back to the generic chart, "
                "not to whichever template the module order happened to yield first",
            )
            self.assertEqual(
                self.ChartTemplate._guess_chart_template(self.country_be),
                "zz_first",
                "a country a template does declare still wins over the generic one",
            )

    def test_parse_csv_builds_sub_records_below_the_first_level(self):
        res = defaultdict(dict)
        self.ChartTemplate._update_csv_vals_from_row(
            self.env["account.tax"],
            res,
            {"id": "tax", "repartition_line_ids/tag_ids/name": "Tag"},
            None,
            "probe.csv",
            2,
        )
        self.assertEqual(
            dict(res),
            {
                "tax": {
                    "repartition_line_ids": [
                        Command.create({"tag_ids": [Command.create({"name": "Tag"})]})
                    ]
                }
            },
            "_resolve_csv_comodel walks a path of any depth, so applying one must too",
        )

    def test_reload_xmlid_mapping_only_reads_company_prefixed_xmlids(self):
        probe = self.ChartTemplate._reload_existing_records(
            self.company, "account.account"
        )[:1]
        self.assertTrue(probe, "the fixture must hold at least one account")

        for xmlid, expected in (
            (f"account.{self.company.id}_receivable", {"receivable"}),
            ("account.account_tag_investing", set()),
            ("account.nounderscore", set()),
            ("l10n_be.1_receivable", set()),
        ):
            with (
                self.subTest(xmlid=xmlid),
                patch.object(
                    type(probe),
                    "get_external_id",
                    lambda records, xmlid=xmlid: {records.id: xmlid},
                ),
            ):
                self.assertEqual(
                    set(self.ChartTemplate._reload_xmlid_mapping(probe)),
                    expected,
                    "only '<company_id>_<template_xmlid>' under the account module "
                    "names a template record; anything else must be skipped rather "
                    "than mis-keyed by splitting on the first underscore",
                )
