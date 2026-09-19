# pylint: disable=bad-whitespace
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import Form, tagged

from .common_report_engine import TestAccountReportsCommon


@tagged("post_install", "-at_install")
class TestTaxReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write(
            {
                "vat": "38972223422",
                "phone_ids": [
                    Command.create({"number": "555-555-5555", "type": "landline"})
                ],
                "email": "test@example.com",
            }
        )

        # Create country data
        cls.fiscal_country = cls.env["res.country"].create(
            {
                "name": "Discworld",
                "code": "DW",
            }
        )

        cls.foreign_country = cls.env["res.country"].create(
            {
                "name": "The Principality of Zeon",
                "code": "PZ",
            }
        )

        # Setup fiscal data
        cls.company_data["company"].write(
            {
                "account_return_periodicity": "trimester",
                "vat": "US12345671",
                "phone_ids": [
                    Command.create({"number": "123456789", "type": "landline"})
                ],
                "email": "test@gmail.com",
            }
        )
        cls.change_company_country(cls.company_data["company"], cls.fiscal_country)

        # Prepare tax groups
        cls.tax_group_1 = cls._instantiate_basic_test_tax_group()
        cls.tax_group_2 = cls._instantiate_basic_test_tax_group()
        cls.tax_group_3 = cls._instantiate_basic_test_tax_group(
            country=cls.foreign_country
        )
        cls.tax_group_4 = cls._instantiate_basic_test_tax_group(
            country=cls.foreign_country
        )

        # Prepare tax accounts
        cls.tax_account_1 = cls.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "250000",
                "account_type": "liability_current",
            }
        )

        cls.tax_account_2 = cls.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "250001",
                "account_type": "liability_current",
            }
        )

        cls.cash_basis_transfer_account = cls.env["account.account"].create(
            {
                "code": "cash.basis.transfer.account",
                "name": "cash_basis_transfer_account",
                "account_type": "income",
                "reconcile": True,
            }
        )

        # ==== Sale taxes: group of two taxes having type_tax_use = 'sale' ====
        cls.sale_tax_percentage_incl_1 = cls.env["account.tax"].create(
            {
                "name": "sale_tax_percentage_incl_1",
                "amount": 20.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
                "tax_group_id": cls.tax_group_1.id,
            }
        )

        cls.sale_tax_percentage_excl = cls.env["account.tax"].create(
            {
                "name": "sale_tax_percentage_excl",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_group_id": cls.tax_group_1.id,
            }
        )

        cls.sale_tax_group = cls.env["account.tax"].create(
            {
                "name": "sale_tax_group",
                "amount_type": "group",
                "type_tax_use": "sale",
                "children_tax_ids": [
                    Command.set(
                        (
                            cls.sale_tax_percentage_incl_1
                            + cls.sale_tax_percentage_excl
                        ).ids
                    )
                ],
            }
        )

        cls.move_sale = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2016-01-01",
                "journal_id": cls.company_data["default_journal_sale"].id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 1320.0,
                            "credit": 0.0,
                            "account_id": cls.company_data[
                                "default_account_receivable"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 120.0,
                            "account_id": cls.tax_account_1.id,
                            "tax_repartition_line_id": cls.sale_tax_percentage_excl.invoice_repartition_line_ids.filtered(
                                lambda x: x.repartition_type == "tax"
                            ).id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 200.0,
                            "account_id": cls.tax_account_1.id,
                            "tax_repartition_line_id": cls.sale_tax_percentage_incl_1.invoice_repartition_line_ids.filtered(
                                lambda x: x.repartition_type == "tax"
                            ).id,
                            "tax_ids": [Command.set(cls.sale_tax_percentage_excl.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 1000.0,
                            "account_id": cls.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [Command.set(cls.sale_tax_group.ids)],
                        }
                    ),
                ],
            }
        )
        cls.move_sale.action_post()

        # ==== Purchase taxes: group of taxes having type_tax_use = 'none' ====

        cls.none_tax_percentage_incl_2 = cls.env["account.tax"].create(
            {
                "name": "none_tax_percentage_incl_2",
                "amount": 20.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "price_include_override": "tax_included",
                "tax_group_id": cls.tax_group_2.id,
            }
        )

        cls.none_tax_percentage_excl = cls.env["account.tax"].create(
            {
                "name": "none_tax_percentage_excl",
                "amount": 30.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "tax_group_id": cls.tax_group_2.id,
            }
        )

        cls.purchase_tax_group = cls.env["account.tax"].create(
            {
                "name": "purchase_tax_group",
                "amount_type": "group",
                "type_tax_use": "purchase",
                "children_tax_ids": [
                    Command.set(
                        (
                            cls.none_tax_percentage_incl_2
                            + cls.none_tax_percentage_excl
                        ).ids
                    )
                ],
            }
        )

        cls.move_purchase = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2016-01-01",
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 3120.0,
                            "account_id": cls.company_data[
                                "default_account_payable"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 720.0,
                            "credit": 0.0,
                            "account_id": cls.tax_account_1.id,
                            "tax_repartition_line_id": cls.none_tax_percentage_excl.invoice_repartition_line_ids.filtered(
                                lambda x: x.repartition_type == "tax"
                            ).id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 400.0,
                            "credit": 0.0,
                            "account_id": cls.tax_account_1.id,
                            "tax_repartition_line_id": cls.none_tax_percentage_incl_2.invoice_repartition_line_ids.filtered(
                                lambda x: x.repartition_type == "tax"
                            ).id,
                            "tax_ids": [Command.set(cls.none_tax_percentage_excl.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "debit": 2000.0,
                            "credit": 0.0,
                            "account_id": cls.company_data[
                                "default_account_expense"
                            ].id,
                            "tax_ids": [Command.set(cls.purchase_tax_group.ids)],
                        }
                    ),
                ],
            }
        )
        cls.move_purchase.action_post()

        # Instantiate test data for fiscal_position option of the tax report (both for checking the report and VAT closing)

        # Create a foreign partner
        cls.test_fpos_foreign_partner = cls.env["res.partner"].create(
            {
                "name": "Mare Cel",
                "country_id": cls.foreign_country.id,
            }
        )

        # Create both a domestic and foreign tax report, and some taxes for them
        cls.domestic_tax_report = cls.env["account.report"].create(
            {
                "name": "The Unseen Tax Report",
                "country_id": cls.fiscal_country.id,
                "root_report_id": cls.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        cls.domestic_sale_tax = cls._add_basic_tax_for_report(
            cls.domestic_tax_report,
            50,
            "sale",
            cls.tax_group_1,
            [
                (30, cls.tax_account_1, False),
                (70, cls.tax_account_1, True),
                (-100, cls.tax_account_2, False),
            ],
        )

        cls.domestic_purchase_tax = cls._add_basic_tax_for_report(
            cls.domestic_tax_report,
            50,
            "purchase",
            cls.tax_group_2,
            [
                (40, cls.tax_account_1, False),
                (60, cls.tax_account_1, True),
                (-100, cls.tax_account_2, False),
            ],
        )

        cls.foreign_tax_report = cls.env["account.report"].create(
            {
                "name": "Miller's Report",
                "country_id": cls.foreign_country.id,
                "root_report_id": cls.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        cls.foreign_sale_tax = cls._add_basic_tax_for_report(
            cls.foreign_tax_report,
            60,
            "sale",
            cls.tax_group_3,
            [
                (80, cls.tax_account_1, False),
                (20, cls.tax_account_1, True),
                (-100, cls.tax_account_2, False),
            ],
        )

        cls.foreign_purchase_tax = cls._add_basic_tax_for_report(
            cls.foreign_tax_report,
            60,
            "purchase",
            cls.tax_group_4,
            [
                (51, cls.tax_account_1, False),
                (49, cls.tax_account_1, True),
                (-100, cls.tax_account_2, False),
            ],
        )

        # Create a fiscal_position to automatically map the default tax for partner "Mare Cel" to our test tax
        cls.env["account.tax"].search([]).original_tax_ids = False
        cls.foreign_vat_fpos = cls.env["account.fiscal.position"].create(
            {
                "name": "Test fpos",
                "auto_apply": True,
                "country_id": cls.foreign_country.id,
                "foreign_vat": "12345",
            }
        )

        cls.domestic_tax_return_type = cls.env["account.return.type"].create(
            {
                "name": "Domestic Tax Return",
                "report_id": cls.domestic_tax_report.id,
                "deadline_periodicity": "trimester",
                "deadline_start_date": "2020-01-01",
            }
        )

        cls.foreign_tax_return_type = cls.env["account.return.type"].create(
            {
                "name": "Foreign Tax Return",
                "report_id": cls.foreign_tax_report.id,
                "deadline_periodicity": "trimester",
                "deadline_start_date": "2020-01-01",
            }
        )

        # Create some domestic invoices (not all in the same closing period)
        cls.init_invoice(
            "out_invoice",
            partner=cls.partner_a,
            invoice_date="2020-12-22",
            post=True,
            amounts=[28000],
            taxes=cls.domestic_sale_tax,
        )
        cls.init_invoice(
            "out_invoice",
            partner=cls.partner_a,
            invoice_date="2021-01-22",
            post=True,
            amounts=[200],
            taxes=cls.domestic_sale_tax,
        )
        cls.init_invoice(
            "out_refund",
            partner=cls.partner_a,
            invoice_date="2021-01-12",
            post=True,
            amounts=[20],
            taxes=cls.domestic_sale_tax,
        )
        cls.init_invoice(
            "in_invoice",
            partner=cls.partner_a,
            invoice_date="2021-03-12",
            post=True,
            amounts=[400],
            taxes=cls.domestic_purchase_tax,
        )
        cls.init_invoice(
            "in_refund",
            partner=cls.partner_a,
            invoice_date="2021-03-20",
            post=True,
            amounts=[60],
            taxes=cls.domestic_purchase_tax,
        )
        cls.init_invoice(
            "in_invoice",
            partner=cls.partner_a,
            invoice_date="2021-04-07",
            post=True,
            amounts=[42000],
            taxes=cls.domestic_purchase_tax,
        )

        # Create some foreign invoices (not all in the same closing period)
        cls.init_invoice(
            "out_invoice",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2020-12-13",
            post=True,
            amounts=[26000],
            taxes=cls.foreign_sale_tax,
        )
        cls.init_invoice(
            "out_invoice",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2021-01-16",
            post=True,
            amounts=[800],
            taxes=cls.foreign_sale_tax,
        )
        cls.init_invoice(
            "out_refund",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2021-01-30",
            post=True,
            amounts=[200],
            taxes=cls.foreign_sale_tax,
        )
        cls.init_invoice(
            "in_invoice",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2021-02-01",
            post=True,
            amounts=[1000],
            taxes=cls.foreign_purchase_tax,
        )
        cls.init_invoice(
            "in_refund",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2021-03-02",
            post=True,
            amounts=[600],
            taxes=cls.foreign_purchase_tax,
        )
        cls.init_invoice(
            "in_refund",
            partner=cls.test_fpos_foreign_partner,
            invoice_date="2021-05-02",
            post=True,
            amounts=[10000],
            taxes=cls.foreign_purchase_tax,
        )

    @classmethod
    def _instantiate_basic_test_tax_group(cls, company=None, country=None):
        company = company or cls.env.company
        vals = {
            "name": "Test tax group",
            "company_ids": company.ids,
            "tax_receivable_account_id": cls.company_data[
                "default_tax_account_receivable"
            ]
            .sudo()
            .copy({"company_ids": company.ids})
            .id,
            "tax_payable_account_id": cls.company_data["default_tax_account_payable"]
            .sudo()
            .copy({"company_ids": company.ids})
            .id,
        }
        if country:
            vals["country_id"] = country.id
        return cls.env["account.tax.group"].sudo().create(vals)

    @classmethod
    def _add_basic_tax_for_report(
        cls,
        tax_report,
        percentage,
        type_tax_use,
        tax_group,
        tax_repartition,
        company=None,
    ):
        """Creates a basic test tax, as well as tax report lines and tags, connecting them all together.

        A tax report line will be created within tax report for each of the elements in tax_repartition,
        for both invoice and refund, so that the resulting repartition lines each reference their corresponding
        report line. Negative tags will be assigned when type_tax_use is 'sale'; positive tags otherwise.

        :param tax_report: The report to create lines for.
        :param percentage: The created tax has amount_type='percent'. This parameter contains its amount.
        :param type_tax_use: type_tax_use of the tax to create
        :param tax_group: The tax group to assign to the created tax.
        :param tax_repartition: List of tuples in the form [(factor_percent, account, use_in_tax_closing)], one tuple
                                for each tax repartition line to create (base lines will be automatically created).
        :param company: The company owning the created tax; defaults to the current environment's company.
        :return: The created account.tax record.
        """
        tax = cls.env["account.tax"].create(
            {
                "name": f"{type_tax_use} - {percentage} - {tax_report.name}",
                "amount": percentage,
                "amount_type": "percent",
                "type_tax_use": type_tax_use,
                "tax_group_id": tax_group.id,
                "country_id": tax_report.country_id.id,
                "company_ids": (company or cls.env.company).ids,
            }
        )

        to_write = {}
        sign = "-" if type_tax_use == "sale" else ""
        for move_type_suffix in ("invoice", "refund"):
            report_line_sequence = (
                tax_report.line_ids[-1].sequence + 1 if tax_report.line_ids else 0
            )

            # Create a report line for the base
            base_report_line_name = f"{tax.id}-{move_type_suffix}-base"
            base_report_line = cls._create_tax_report_line(
                base_report_line_name,
                tax_report,
                tag_name=sign + base_report_line_name,
                sequence=report_line_sequence,
            )
            report_line_sequence += 1

            base_tag = base_report_line.expression_ids._get_matching_tags()

            repartition_vals = [
                Command.clear(),
                Command.create({"repartition_type": "base", "tag_ids": base_tag.ids}),
            ]

            for factor_percent, account, use_in_tax_closing in tax_repartition:
                # Create a report line for the repartition line
                tax_report_line_name = f"{tax.id}-{move_type_suffix}-{factor_percent}"
                tax_report_line = cls._create_tax_report_line(
                    tax_report_line_name,
                    tax_report,
                    tag_name=sign + tax_report_line_name,
                    sequence=report_line_sequence,
                )
                report_line_sequence += 1

                tax_tag = tax_report_line.expression_ids._get_matching_tags()

                repartition_vals.append(
                    Command.create(
                        {
                            "account_id": account.id if account else None,
                            "factor_percent": factor_percent,
                            "use_in_tax_closing": use_in_tax_closing,
                            "tag_ids": tax_tag.ids,
                        }
                    )
                )

            to_write[f"{move_type_suffix}_repartition_line_ids"] = repartition_vals

        tax.write(to_write)

        return tax

    def _assert_tax_closing(
        self,
        company,
        date_from,
        date_to,
        return_type,
        closing_vals_by_company,
        tax_unit=None,
    ):
        tax_return = self.env["account.return"].create(
            {
                "name": "Return",
                "date_from": date_from,
                "date_to": date_to,
                "type_id": return_type.id,
                "company_id": company.id,
                "tax_unit_id": tax_unit.id if tax_unit else False,
            }
        )
        with self.allow_pdf_render():
            tax_return.action_validate(bypass_failing_tests=True)

        self.assertEqual(len(closing_vals_by_company), len(tax_return.closing_move_ids))
        for closing_move in tax_return.closing_move_ids:
            expected_vals = closing_vals_by_company[closing_move.company_id]
            self.assertRecordValues(closing_move.line_ids, expected_vals)

    def test_tax_report_domestic_monocompany(self):
        options = self._generate_options(
            self.domestic_tax_report, "2021-01-01", "2021-03-31"
        )

        self.assertLinesValues(
            self.domestic_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0, 1],
            [
                # out_invoice
                (f"{self.domestic_sale_tax.id}-invoice-base", 200),
                (f"{self.domestic_sale_tax.id}-invoice-30", 30),
                (f"{self.domestic_sale_tax.id}-invoice-70", 70),
                (f"{self.domestic_sale_tax.id}-invoice--100", -100),
                # out_refund
                (f"{self.domestic_sale_tax.id}-refund-base", -20),
                (f"{self.domestic_sale_tax.id}-refund-30", -3),
                (f"{self.domestic_sale_tax.id}-refund-70", -7),
                (f"{self.domestic_sale_tax.id}-refund--100", 10),
                # in_invoice
                (f"{self.domestic_purchase_tax.id}-invoice-base", 400),
                (f"{self.domestic_purchase_tax.id}-invoice-40", 80),
                (f"{self.domestic_purchase_tax.id}-invoice-60", 120),
                (f"{self.domestic_purchase_tax.id}-invoice--100", -200),
                # in_refund
                (f"{self.domestic_purchase_tax.id}-refund-base", -60),
                (f"{self.domestic_purchase_tax.id}-refund-40", -12),
                (f"{self.domestic_purchase_tax.id}-refund-60", -18),
                (f"{self.domestic_purchase_tax.id}-refund--100", 30),
            ],
            options,
        )

        self._assert_tax_closing(
            self.env.company,
            "2021-01-01",
            "2021-03-31",
            self.domestic_tax_return_type,
            {
                self.env.company: [
                    # 0.5 * 0.7 * (200 - 20) = 63
                    {"debit": 63.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                    # 0.5 * 0.6 * (400 - 60) = 102
                    {
                        "debit": 0.0,
                        "credit": 102.0,
                        "account_id": self.tax_account_1.id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 63.0,
                        "account_id": self.tax_group_1.tax_payable_account_id.id,
                    },
                    {
                        "debit": 102.0,
                        "credit": 0.0,
                        "account_id": self.tax_group_2.tax_receivable_account_id.id,
                    },
                ],
            },
        )

    def test_tax_report_foreign_monocompany(self):
        """Test tax report's content with a foreign VAT fiscal position."""
        options = self._generate_options(
            self.foreign_tax_report, "2021-01-01", "2021-03-31"
        )

        self.assertLinesValues(
            self.foreign_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0, 1],
            [
                # out_invoice
                (f"{self.foreign_sale_tax.id}-invoice-base", 800),
                (f"{self.foreign_sale_tax.id}-invoice-80", 384),
                (f"{self.foreign_sale_tax.id}-invoice-20", 96),
                (f"{self.foreign_sale_tax.id}-invoice--100", -480),
                # out_refund
                (f"{self.foreign_sale_tax.id}-refund-base", -200),
                (f"{self.foreign_sale_tax.id}-refund-80", -96),
                (f"{self.foreign_sale_tax.id}-refund-20", -24),
                (f"{self.foreign_sale_tax.id}-refund--100", 120),
                # in_invoice
                (f"{self.foreign_purchase_tax.id}-invoice-base", 1000),
                (f"{self.foreign_purchase_tax.id}-invoice-51", 306),
                (f"{self.foreign_purchase_tax.id}-invoice-49", 294),
                (f"{self.foreign_purchase_tax.id}-invoice--100", -600),
                # in_refund
                (f"{self.foreign_purchase_tax.id}-refund-base", -600),
                (f"{self.foreign_purchase_tax.id}-refund-51", -183.6),
                (f"{self.foreign_purchase_tax.id}-refund-49", -176.4),
                (f"{self.foreign_purchase_tax.id}-refund--100", 360),
            ],
            options,
        )

        self._assert_tax_closing(
            self.env.company,
            "2021-01-01",
            "2021-03-31",
            self.foreign_tax_return_type,
            {
                self.env.company: [
                    # 0.6 * 0.2 * (800 - 200) = 72
                    {"debit": 72.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                    # 0.6 * 0.49 * (1000 - 600) = 117.6
                    {
                        "debit": 0.0,
                        "credit": 117.6,
                        "account_id": self.tax_account_1.id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 72.0,
                        "account_id": self.tax_group_3.tax_payable_account_id.id,
                    },
                    {
                        "debit": 117.6,
                        "credit": 0.0,
                        "account_id": self.tax_group_4.tax_receivable_account_id.id,
                    },
                ],
            },
        )

    def test_tax_report_grid(self):
        company = self.company_data["company"]

        # We generate a tax report with the following layout
        # /Base
        #   - Base 42%
        #   - Base 11%
        # /Tax
        #   - Tax 42%
        #       - 10.5%
        #       - 31.5%
        #   - Tax 11%
        #   - Tax -100%
        # /Tax difference (42% - 11%)

        tax_report = self.env["account.report"].create(
            {
                "name": "Test",
                "country_id": company.account_config_id.account_fiscal_country_id.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        # We create the lines in a different order from the one they have in report,
        # so that we ensure sequence is taken into account properly when rendering the report
        tax_section = self._create_tax_report_line(
            "Tax",
            tax_report,
            sequence=4,
            formula="tax_42.balance + tax_11.balance + tax_neg_100.balance",
        )
        base_section = self._create_tax_report_line(
            "Base", tax_report, sequence=1, formula="base_11.balance + base_42.balance"
        )
        base_42_line = self._create_tax_report_line(
            "Base 42%",
            tax_report,
            sequence=2,
            parent_line=base_section,
            code="base_42",
            tag_name="-base_42",
        )
        base_11_line = self._create_tax_report_line(
            "Base 11%",
            tax_report,
            sequence=3,
            parent_line=base_section,
            code="base_11",
            tag_name="-base_11",
        )
        tax_42_section = self._create_tax_report_line(
            "Tax 42%",
            tax_report,
            sequence=5,
            parent_line=tax_section,
            code="tax_42",
            formula="tax_31_5.balance + tax_10_5.balance",
        )
        tax_31_5_line = self._create_tax_report_line(
            "Tax 31.5%",
            tax_report,
            sequence=7,
            parent_line=tax_42_section,
            code="tax_31_5",
            tag_name="-tax_31_5",
        )
        tax_10_5_line = self._create_tax_report_line(
            "Tax 10.5%",
            tax_report,
            sequence=6,
            parent_line=tax_42_section,
            code="tax_10_5",
            tag_name="-tax_10_5",
        )
        tax_11_line = self._create_tax_report_line(
            "Tax 11%",
            tax_report,
            sequence=8,
            parent_line=tax_section,
            code="tax_11",
            tag_name="-tax_11",
        )
        tax_neg_100_line = self._create_tax_report_line(
            "Tax -100%",
            tax_report,
            sequence=9,
            parent_line=tax_section,
            code="tax_neg_100",
            tag_name="tax_neg_100",
        )
        self._create_tax_report_line(
            "Tax difference (42%-11%)",
            tax_report,
            sequence=10,
            formula="tax_42.balance - tax_11.balance",
        )

        # Create two taxes linked to report lines
        tax_11 = self.env["account.tax"].create(
            {
                "name": "Impôt sur les revenus",
                "amount": 11,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": self._get_tag_ids(base_11_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_11_line.expression_ids),
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": self._get_tag_ids(base_11_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_11_line.expression_ids),
                        }
                    ),
                ],
            }
        )

        tax_42 = self.env["account.tax"].create(
            {
                "name": "Impôt sur les revenants",
                "amount": 42,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": self._get_tag_ids(base_42_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 25,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_10_5_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 75,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_31_5_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": -100,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(
                                tax_neg_100_line.expression_ids
                            ),
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": self._get_tag_ids(base_42_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 25,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_10_5_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 75,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(tax_31_5_line.expression_ids),
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": -100,
                            "repartition_type": "tax",
                            "tag_ids": self._get_tag_ids(
                                tax_neg_100_line.expression_ids
                            ),
                        }
                    ),
                ],
            }
        )

        # Create an invoice using the tax we just made
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Turlututu",
                            "price_unit": 100.0,
                            "quantity": 1,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [Command.set((tax_11 + tax_42).ids)],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        # Generate the report and check the results
        report = tax_report
        options = self._generate_options(report, invoice.date, invoice.date)

        # Invalidate the cache to ensure the lines will be fetched in the right order.
        self.env.invalidate_all()

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                        Balance
            [0, 1],
            [
                ("Base", 200),
                ("Base 42%", 100),
                ("Base 11%", 100),
                ("Total Base", 200),
                ("Tax", 95),
                ("Tax 42%", 42),
                ("Tax 10.5%", 10.5),
                ("Tax 31.5%", 31.5),
                ("Total Tax 42%", 42),
                ("Tax 11%", 11),
                ("Tax -100%", 42),
                ("Total Tax", 95),
                ("Tax difference (42%-11%)", 31),
            ],
            options,
        )

        # We refund the invoice
        refund_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "reason": "Test refund tax repartition",
                    "journal_id": invoice.journal_id.id,
                    "date": invoice.date,
                }
            )
        )
        refund_wizard.modify_moves()

        # We check the taxes on refund have impacted the report properly (everything should be 0)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                         Balance
            [0, 1],
            [
                ("Base", 0.0),
                ("Base 42%", 0.0),
                ("Base 11%", 0.0),
                ("Total Base", 0.0),
                ("Tax", 0.0),
                ("Tax 42%", 0.0),
                ("Tax 10.5%", 0.0),
                ("Tax 31.5%", 0.0),
                ("Total Tax 42%", 0.0),
                ("Tax 11%", 0.0),
                ("Tax -100%", 0.0),
                ("Total Tax", 0.0),
                ("Tax difference (42%-11%)", 0.0),
            ],
            options,
        )

    def _create_caba_taxes_for_report_lines(self, report_lines_dict, company):
        """Creates cash basis taxes with a specific test repartition and maps them to
        the provided tax_report lines.

        :param report_lines_dict:  A dictionary mapping type_tax_use values to
                                   tax report line records
        :param company:            Unused.

        :return:                   The created account.tax objects
        """
        return self.env["account.tax"].create(
            [
                {
                    "name": "Impôt sur tout ce qui bouge",
                    "amount": "20",
                    "amount_type": "percent",
                    "type_tax_use": tax_type,
                    "tax_exigibility": "on_payment",
                    "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                    "invoice_repartition_line_ids": [
                        Command.create(
                            {
                                "repartition_type": "base",
                                "tag_ids": self._get_tag_ids(
                                    report_line.expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "factor_percent": 25,
                                "repartition_type": "tax",
                                "tag_ids": self._get_tag_ids(
                                    report_line.expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "factor_percent": 75,
                                "repartition_type": "tax",
                                "tag_ids": self._get_tag_ids(
                                    report_line.expression_ids
                                ),
                            }
                        ),
                    ],
                    "refund_repartition_line_ids": [
                        Command.create(
                            {
                                "repartition_type": "base",
                                "tag_ids": self._get_tag_ids(
                                    report_line.expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "factor_percent": 25,
                                "repartition_type": "tax",
                                "tag_ids": self._get_tag_ids(
                                    report_line.expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "factor_percent": 75,
                                "repartition_type": "tax",
                            }
                        ),
                    ],
                }
                for tax_type, report_line in report_lines_dict.items()
            ]
        )

    def _create_taxes_for_report_lines(self, report_lines_dict, company):
        return self.env["account.tax"].create(
            [
                {
                    "name": "Impôt sur tout ce qui bouge",
                    "amount": "20",
                    "amount_type": "percent",
                    "type_tax_use": tax_type,
                    "invoice_repartition_line_ids": [
                        Command.create(
                            {
                                "repartition_type": "base",
                                "tag_ids": self._get_tag_ids(
                                    report_line[0].expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "repartition_type": "tax",
                                "tag_ids": self._get_tag_ids(
                                    report_line[1].expression_ids
                                ),
                            }
                        ),
                    ],
                    "refund_repartition_line_ids": [
                        Command.create(
                            {
                                "repartition_type": "base",
                                "tag_ids": self._get_tag_ids(
                                    report_line[0].expression_ids
                                ),
                            }
                        ),
                        Command.create(
                            {
                                "repartition_type": "tax",
                                "tag_ids": self._get_tag_ids(
                                    report_line[1].expression_ids
                                ),
                            }
                        ),
                    ],
                }
                for tax_type, report_line in report_lines_dict.items()
            ]
        )

    def _run_caba_generic_test(
        self,
        expected_columns,
        expected_lines,
        on_invoice_created=None,
        on_all_invoices_created=None,
        invoice_generator=None,
    ):
        """Generic test function called by several cash basis tests.

        Creates a sale and a purchase tax, each associated with a new tax report line via
        _create_caba_taxes_for_report_lines, then creates an invoice AND a refund for each
        of these taxes, and finally compares the tax report to the expected values.

        :param expected_columns:          The columns we want the final tax report to contain

        :param expected_lines:            The lines we want the final tax report to contain

        :param on_invoice_created:        A function to be called when a single invoice has
                                          just been created, taking the invoice as a parameter
                                          (This can be used to reconcile the invoice with something, for example)

        :param on_all_invoices_created:   A function to be called when all the invoices corresponding
                                          to a tax type have been created, taking the
                                          recordset of all these invoices as a parameter
                                          (Use it to reconcile invoice and credit note together, for example)

        :param invoice_generator:         A function used to generate an invoice. A default
                                          one is called if none is provided, creating
                                          an invoice with a single line amounting to 100,
                                          with the provided tax set on it.
        """

        def default_invoice_generator(inv_type, partner, account, date, tax):
            return self.env["account.move"].create(
                {
                    "move_type": inv_type,
                    "partner_id": partner.id,
                    "invoice_date": date,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "quantity": 1,
                                "account_id": account.id,
                                "price_unit": 100,
                                "tax_ids": [Command.set(tax.ids)],
                            }
                        )
                    ],
                }
            )

        today = fields.Date.today()

        company = self.company_data["company"]
        company.account_config_id.tax_exigibility = True
        partner = self.env["res.partner"].create({"name": "Char Aznable"})

        # Create a tax report
        tax_report = self.env["account.report"].create(
            {
                "name": "Test",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        # We create some report lines
        report_lines_dict = {
            "sale": self._create_tax_report_line(
                "Sale", tax_report, sequence=1, tag_name="-sale"
            ),
            "purchase": self._create_tax_report_line(
                "Purchase", tax_report, sequence=2, tag_name="purchase"
            ),
        }

        # We create a sale and a purchase tax, linked to our report lines' tags.
        # These taxes are asymmetric (their 75% repartition line does not impact the report line
        # at refund), which gives complete coverage and does not shadow any result due, for
        # example, to some undesired swapping between debit and credit.
        taxes = self._create_caba_taxes_for_report_lines(report_lines_dict, company)

        # Create invoice and refund using the tax we just made
        invoice_types = {
            "sale": ("out_invoice", "out_refund"),
            "purchase": ("in_invoice", "in_refund"),
        }

        account_types = {
            "sale": "income",
            "purchase": "expense",
        }
        for tax in taxes:
            invoices = self.env["account.move"]
            account = self.env["account.account"].search(
                [
                    ("company_ids", "=", company.id),
                    ("account_type", "=", account_types[tax.type_tax_use]),
                ],
                limit=1,
            )
            for inv_type in invoice_types[tax.type_tax_use]:
                invoice = (invoice_generator or default_invoice_generator)(
                    inv_type, partner, account, today, tax
                )
                invoice.action_post()
                invoices += invoice

                if on_invoice_created:
                    on_invoice_created(invoice)

            if on_all_invoices_created:
                on_all_invoices_created(invoices)

        # Generate the report and check the results
        # We check the taxes on invoice have impacted the report properly
        options = self._generate_options(tax_report, date_from=today, date_to=today)
        inv_report_lines = tax_report._get_lines(options)
        self.assertLinesValues(
            inv_report_lines, expected_columns, expected_lines, options
        )

    def _register_full_payment_for_invoice(self, invoice):
        """Fully pay the invoice, so that the cash basis entries are created"""
        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "payment_date": invoice.date,
            }
        )._create_payments()

    @freeze_time("2023-10-05 02:00:00")
    def test_tax_report_grid_cash_basis(self):
        """Cash basis moves created for taxes based on payments are handled differently
        by the report; their sign must be managed properly.
        """
        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [0, 1],
            [
                ("Sale", 15),
                ("Purchase", 15),
            ],
            on_invoice_created=self._register_full_payment_for_invoice,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_tax_report_grid_cash_basis_refund(self):
        """Cash basis moves created for taxes based on payments are handled differently
        by the report; their sign must be managed properly. Here an invoice is
        reconciled with a refund (created separately, so not cancelling it).
        """

        def reconcile_opposite_types(invoices):
            """Reconciles the created invoices with their matching refund."""
            invoices.mapped("line_ids").filtered(
                lambda x: x.account_type in ("asset_receivable", "liability_payable")
            ).reconcile()

        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [0, 1],
            [
                ("Sale", 15),
                ("Purchase", 15),
            ],
            on_all_invoices_created=reconcile_opposite_types,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_tax_report_grid_cash_basis_misc_pmt(self):
        """Cash basis moves created for taxes based on payments are handled differently
        by the report; their sign must be managed properly. Here the invoice is paid
        with a misc operation instead of a payment.
        """

        def reconcile_with_misc_pmt(invoice):
            """Create a misc operation equivalent to a full payment and reconciles
            the invoice with it.
            """
            # Pay the invoice with a misc operation simulating a payment, so that the cash basis entries are created
            invoice_reconcilable_line = invoice.line_ids.filtered(
                lambda x: x.account_type in ("liability_payable", "asset_receivable")
            )
            account = (
                invoice.line_ids - invoice_reconcilable_line
            ).account_id - self.cash_basis_transfer_account
            pmt_move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": invoice.date,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": invoice_reconcilable_line.account_id.id,
                                "debit": invoice_reconcilable_line.credit,
                                "credit": invoice_reconcilable_line.debit,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": account.id,
                                "credit": invoice_reconcilable_line.credit,
                                "debit": invoice_reconcilable_line.debit,
                            }
                        ),
                    ],
                }
            )
            pmt_move.action_post()
            payment_reconcilable_line = pmt_move.line_ids.filtered(
                lambda x: x.account_type in ("liability_payable", "asset_receivable")
            )
            (invoice_reconcilable_line + payment_reconcilable_line).reconcile()

        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [0, 1],
            [
                ("Sale", 15),
                ("Purchase", 15),
            ],
            on_invoice_created=reconcile_with_misc_pmt,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_caba_no_payment(self):
        """The cash basis taxes of an unpaid invoice should
        never impact the report.
        """
        self._run_caba_generic_test(
            #   Name                      Balance
            [0, 1],
            [
                ("Sale", 0.0),
                ("Purchase", 0.0),
            ],
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_caba_half_payment(self):
        """Paying half the amount of the invoice should report half the
        base and tax amounts.
        """

        def register_half_payment_for_invoice(invoice):
            """Pay half of the invoice, so that the cash basis entries are created"""
            payment_method_id = (
                self.inbound_payment_channel
                if invoice.is_inbound()
                else self.outbound_payment_channel
            )
            self.env["account.payment.register"].with_context(
                active_ids=invoice.ids, active_model="account.move"
            ).create(
                {
                    "amount": invoice.amount_residual / 2,
                    "payment_date": invoice.date,
                    "payment_channel_id": payment_method_id.id,
                }
            )._create_payments()

        # 50 (base, invoice) - 50 (base, refund) + 10 (tax, invoice) - 2.5 (25% tax, refund) = 7.5
        self._run_caba_generic_test(
            #   Name                     Balance
            [0, 1],
            [
                ("Sale", 7.5),
                ("Purchase", 7.5),
            ],
            on_invoice_created=register_half_payment_for_invoice,
        )

    def test_caba_mixed_generic_report(self):
        """Tests mixing taxes with different tax exigibilities displays correct amounts
        in the generic tax report.
        """
        self.env.company.account_config_id.tax_exigibility = True
        # Create taxes
        regular_tax = self.env["account.tax"].create(
            {
                "name": "Regular",
                "amount": 42,
                "amount_type": "percent",
                "type_tax_use": "sale",
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )

        caba_tax = self.env["account.tax"].create(
            {
                "name": "Cash Basis",
                "amount": 10,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )

        # Create an invoice using them, and post it
        invoice = self.init_invoice(
            "out_invoice",
            invoice_date="2021-07-01",
            post=True,
            amounts=[100],
            taxes=regular_tax + caba_tax,
            company=self.company_data["company"],
        )

        # Check the report only contains non-caba things
        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice.date, invoice.date)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                         Net               Tax
            [0, 1, 2],
            [
                ("Sales", "", 42),
                ("Regular (42.0%)", 100, 42),
                ("Total Sales", "", 42),
            ],
            options,
        )

        # Pay half of the invoice
        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "amount": 76,
                "payment_date": invoice.date,
                "payment_channel_id": self.outbound_payment_channel.id,
            }
        )._create_payments()

        # Check the report again: half the cash basis should be there
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                          Net               Tax
            [0, 1, 2],
            [
                ("Sales", "", 47),
                ("Regular (42.0%)", 100, 42),
                ("Cash Basis (10.0%)", 50, 5),
                ("Total Sales", "", 47),
            ],
            options,
        )

        # Pay the rest
        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "amount": 76,
                "payment_date": invoice.date,
                "payment_channel_id": self.outbound_payment_channel.id,
            }
        )._create_payments()

        # Check everything is in the report
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                          Net              Tax
            [0, 1, 2],
            [
                ("Sales", "", 52),
                ("Regular (42.0%)", 100, 42),
                ("Cash Basis (10.0%)", 100, 10),
                ("Total Sales", "", 52),
            ],
            options,
        )

    def test_tax_report_mixed_exigibility_affect_base_generic_invoice(self):
        """Tests mixing caba and non-caba taxes with one of them affecting the base
        of the other works properly on invoices for the generic report.
        """
        self.env.company.account_config_id.tax_exigibility = True
        # Create taxes
        regular_tax = self.env["account.tax"].create(
            {
                "name": "Regular",
                "amount": 42,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "include_base_amount": True,
                "sequence": 0,
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )

        caba_tax = self.env["account.tax"].create(
            {
                "name": "Cash Basis",
                "amount": 10,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "include_base_amount": True,
                "sequence": 1,
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )

        report = self.env.ref("account.generic_tax_report")
        # Case 1: on_invoice tax affecting on_payment tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            "2021-07-01",
            report,
            # Name,                          Net,               Tax
            [0, 1, 2],
            # Before payment
            [
                ("Sales", "", 42),
                ("Regular (42.0%)", 100, 42),
                ("Total Sales", "", 42),
            ],
            # After paying 30%
            [
                ("Sales", "", 46.26),
                ("Regular (42.0%)", 100, 42),
                ("Cash Basis (10.0%)", 42.6, 4.26),
                ("Total Sales", "", 46.26),
            ],
            # After full payment
            [
                ("Sales", "", 56.2),
                ("Regular (42.0%)", 100, 42),
                ("Cash Basis (10.0%)", 142, 14.2),
                ("Total Sales", "", 56.2),
            ],
        )

        # Change sequence
        caba_tax.sequence = 0
        regular_tax.sequence = 1

        # Case 2: on_payment tax affecting on_invoice tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            "2021-07-02",
            report,
            #   Name                         Net                Tax
            [0, 1, 2],
            # Before payment
            [
                ("Sales", "", 46.2),
                ("Regular (42.0%)", 110, 46.2),
                ("Total Sales", "", 46.2),
            ],
            # After paying 30%
            [
                ("Sales", "", 49.2),
                ("Cash Basis (10.0%)", 30, 3),
                ("Regular (42.0%)", 110, 46.2),
                ("Total Sales", "", 49.2),
            ],
            # After full payment
            [
                ("Sales", "", 56.2),
                ("Cash Basis (10.0%)", 100, 10),
                ("Regular (42.0%)", 110, 46.2),
                ("Total Sales", "", 56.2),
            ],
        )

    def test_tax_report_mixed_exigibility_affect_base_tags(self):
        """Tests mixing caba and non-caba taxes with one of them affecting the base
        of the other works properly on invoices for the tax report.
        """
        self.env.company.account_config_id.tax_exigibility = True
        # Create taxes
        tax_report = self.env["account.report"].create(
            {
                "name": "Sokovia Accords",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        regular_tax = self._add_basic_tax_for_report(
            tax_report, 42, "sale", self.tax_group_1, [(100, None, True)]
        )
        caba_tax = self._add_basic_tax_for_report(
            tax_report, 10, "sale", self.tax_group_1, [(100, None, True)]
        )

        regular_tax.write(
            {
                "include_base_amount": True,
                "sequence": 0,
            }
        )
        caba_tax.write(
            {
                "include_base_amount": True,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "sequence": 1,
            }
        )

        # Case 1: on_invoice tax affecting on_payment tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            "2021-07-01",
            tax_report,
            #   Name                                       Balance
            [0, 1],
            # Before payment
            [
                (f"{regular_tax.id}-invoice-base", 100),
                (f"{regular_tax.id}-invoice-100", 42),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 0.0),
                (f"{caba_tax.id}-invoice-100", 0.0),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
            # After paying 30%
            [
                (f"{regular_tax.id}-invoice-base", 100),
                (f"{regular_tax.id}-invoice-100", 42),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 42.6),
                (f"{caba_tax.id}-invoice-100", 4.26),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
            # After full payment
            [
                (f"{regular_tax.id}-invoice-base", 100),
                (f"{regular_tax.id}-invoice-100", 42),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 142),
                (f"{caba_tax.id}-invoice-100", 14.2),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
        )

        # Change sequence
        caba_tax.sequence = 0
        regular_tax.sequence = 1

        # Case 2: on_payment tax affecting on_invoice tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            "2021-07-02",
            tax_report,
            #   Name                                       Balance
            [0, 1],
            # Before payment
            [
                (f"{regular_tax.id}-invoice-base", 110),
                (f"{regular_tax.id}-invoice-100", 46.2),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 0.0),
                (f"{caba_tax.id}-invoice-100", 0.0),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
            # After paying 30%
            [
                (f"{regular_tax.id}-invoice-base", 110),
                (f"{regular_tax.id}-invoice-100", 46.2),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 30),
                (f"{caba_tax.id}-invoice-100", 3),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
            # After full payment
            [
                (f"{regular_tax.id}-invoice-base", 110),
                (f"{regular_tax.id}-invoice-100", 46.2),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 100),
                (f"{caba_tax.id}-invoice-100", 10),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
        )

    def _run_check_suite_mixed_exigibility_affect_base(
        self,
        taxes,
        invoice_date,
        report,
        report_columns,
        vals_not_paid,
        vals_30_percent_paid,
        vals_fully_paid,
    ):
        # Create an invoice using them
        invoice = self.init_invoice(
            "out_invoice",
            invoice_date=invoice_date,
            post=True,
            amounts=[100],
            taxes=taxes,
            company=self.company_data["company"],
        )

        # Check the report
        report_options = self._generate_options(report, invoice.date, invoice.date)
        self.assertLinesValues(
            report._get_lines(report_options),
            report_columns,
            vals_not_paid,
            report_options,
        )

        # Pay 30% of the invoice
        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "amount": invoice.amount_residual * 0.3,
                "payment_date": invoice.date,
                "payment_channel_id": self.outbound_payment_channel.id,
            }
        )._create_payments()

        # Check the report again: 30% of the caba amounts should be there
        self.assertLinesValues(
            report._get_lines(report_options),
            report_columns,
            vals_30_percent_paid,
            report_options,
        )

        # Pay the rest: total caba amounts should be there
        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "payment_date": invoice.date,
                "payment_channel_id": self.outbound_payment_channel.id,
            }
        )._create_payments()

        # Check the report
        self.assertLinesValues(
            report._get_lines(report_options),
            report_columns,
            vals_fully_paid,
            report_options,
        )

    def test_caba_always_exigible(self):
        """Misc operations without payable nor receivable lines must always be exigible,
        whatever the tax_exigibility configured on their taxes.
        """
        tax_report = self.env["account.report"].create(
            {
                "name": "Laplace's Box",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        regular_tax = self._add_basic_tax_for_report(
            tax_report, 42, "sale", self.tax_group_1, [(100, None, True)]
        )
        caba_tax = self._add_basic_tax_for_report(
            tax_report, 10, "sale", self.tax_group_1, [(100, None, True)]
        )

        regular_tax.write(
            {
                "include_base_amount": True,
                "sequence": 0,
            }
        )
        caba_tax.write(
            {
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "sequence": 1,
            }
        )

        # Create a misc operation using various combinations of our taxes
        move = self.env["account.move"].create(
            {
                "date": "2021-08-01",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test with %s" % ", ".join(taxes.mapped("name")),
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "credit": 100,
                            "tax_ids": [Command.set(taxes.ids)],
                        }
                    )
                    for taxes in (caba_tax, regular_tax, caba_tax + regular_tax)
                ]
                + [
                    Command.create(
                        {
                            "name": "Balancing line",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "debit": 408.2,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )

        move.action_post()

        self.assertTrue(
            move.always_tax_exigible,
            "A move without payable/receivable line should always be exigible, whatever its taxes.",
        )

        # Check tax report by grid
        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                        Balance
            [0, 1],
            [
                (f"{regular_tax.id}-invoice-base", 200),
                (f"{regular_tax.id}-invoice-100", 84),
                (f"{regular_tax.id}-refund-base", 0.0),
                (f"{regular_tax.id}-refund-100", 0.0),
                (f"{caba_tax.id}-invoice-base", 242),
                (f"{caba_tax.id}-invoice-100", 24.2),
                (f"{caba_tax.id}-refund-base", 0.0),
                (f"{caba_tax.id}-refund-100", 0.0),
            ],
            report_options,
        )

        # Check generic tax report
        tax_report = self.env.ref("account.generic_tax_report")
        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                               Net           Tax
            [0, 1, 2],
            [
                ("Sales", "", 108.2),
                (f"{regular_tax.name} (42.0%)", 200, 84),
                (f"{caba_tax.name} (10.0%)", 242, 24.2),
                ("Total Sales", "", 108.2),
            ],
            report_options,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_tax_report_grid_caba_negative_inv_line(self):
        """Tests cash basis taxes work properly in case a line of the invoice
        has been made with a negative quantities and taxes (causing debit and
        credit to be inverted on the base line).
        """

        def neg_line_invoice_generator(inv_type, partner, account, date, tax):
            """Invoices created here have a line at 100 with a negative quantity of -1.
            They also required a second line (here 200), so that the invoice doesn't
            have a negative total, but we don't put any tax on it.
            """
            return self.env["account.move"].create(
                {
                    "move_type": inv_type,
                    "partner_id": partner.id,
                    "invoice_date": date,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "quantity": -1,
                                "account_id": account.id,
                                "price_unit": 100,
                                "tax_ids": [Command.set(tax.ids)],
                            }
                        ),
                        # Second line, so that the invoice doesn't have a negative total
                        Command.create(
                            {
                                "name": "test",
                                "quantity": 1,
                                "account_id": account.id,
                                "price_unit": 200,
                                "tax_ids": [],
                            }
                        ),
                    ],
                }
            )

        # -100 (base, invoice) + 100 (base, refund) - 20 (tax, invoice) + 5 (25% tax, refund) = -15
        self._run_caba_generic_test(
            #   Name                      Balance
            [0, 1],
            [
                ("Sale", -15),
                ("Purchase", -15),
            ],
            on_invoice_created=self._register_full_payment_for_invoice,
            invoice_generator=neg_line_invoice_generator,
        )

    def test_tax_report_multi_inv_line_no_rep_account(self):
        """Tests the behavior of the tax report when using a tax without any
        repartition account (hence doing its tax lines on the base account),
        and using the tax on two lines (to make sure grouping is handled
        properly by the report).
        We do that for both regular and cash basis taxes.
        """
        # Create taxes
        regular_tax = self.env["account.tax"].create(
            {
                "name": "Regular",
                "amount": 42,
                "amount_type": "percent",
                "type_tax_use": "sale",
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )

        caba_tax = self.env["account.tax"].create(
            {
                "name": "Cash Basis",
                "amount": 42,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                # We use default repartition: 1 base line, 1 100% tax line
            }
        )
        self.env.company.account_config_id.tax_exigibility = True

        # Make one invoice of 2 lines for each of our taxes
        invoice_date = fields.Date.from_string("2021-04-01")
        other_account_revenue = self.company_data["default_account_revenue"].copy()

        regular_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line 1",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 100,
                            "tax_ids": [Command.set(regular_tax.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "name": "line 2",
                            "account_id": other_account_revenue.id,
                            "price_unit": 100,
                            "tax_ids": [Command.set(regular_tax.ids)],
                        }
                    ),
                ],
            }
        )

        caba_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line 1",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 100,
                            "tax_ids": [Command.set(caba_tax.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "name": "line 2",
                            "account_id": other_account_revenue.id,
                            "price_unit": 100,
                            "tax_ids": [Command.set(caba_tax.ids)],
                        }
                    ),
                ],
            }
        )

        # Post the invoices
        regular_invoice.action_post()
        caba_invoice.action_post()

        # Pay cash basis invoice
        self.env["account.payment.register"].with_context(
            active_ids=caba_invoice.ids, active_model="account.move"
        ).create(
            {
                "payment_date": invoice_date,
            }
        )._create_payments()

        # Check the generic report
        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice_date, invoice_date)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                         Net               Tax
            [0, 1, 2],
            [
                ("Sales", "", 168),
                ("Regular (42.0%)", 200, 84),
                ("Cash Basis (42.0%)", 200, 84),
                ("Total Sales", "", 168),
            ],
            options,
        )

    def test_tax_unit(self):
        tax_unit_report = self.env["account.report"].create(
            {
                "name": "And now for something completely different",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        company_1 = self.company_data["company"]
        company_2 = self.company_data_2["company"]
        company_3 = self.setup_other_company(name="Company 3")["company"]
        unit_companies = company_1 + company_2
        all_companies = unit_companies + company_3

        company_2.currency_id = company_1.currency_id

        tax_unit = self.env["account.tax.unit"].create(
            {
                "name": "One unit to rule them all",
                "country_id": self.fiscal_country.id,
                "vat": "DW1234567890",
                "company_ids": [Command.set(unit_companies.ids)],
                "main_company_id": company_1.id,
            }
        )
        self._instantiate_basic_test_tax_group(company_2)
        self._instantiate_basic_test_tax_group(company_3)

        created_taxes = {}
        tax_accounts = {}
        invoice_date = fields.Date.from_string("2018-01-01")
        tax_accounts_map = {}
        for index, company in enumerate(all_companies):
            # Make sure the fiscal country is what we want
            self.change_company_country(company, self.fiscal_country)

            # Create a tax for this report
            tax_account = self.env["account.account"].create(
                {
                    "name": "Tax unit test tax account",
                    "code": "test.tax.unit",
                    "account_type": "asset_current",
                    "company_ids": [Command.link(company.id)],
                }
            )
            tax_group = self.env["account.tax.group"].search(
                [("company_ids", "in", company.ids), ("name", "=", "Test tax group")],
                limit=1,
            )

            tax_accounts_map[company] = {
                "tax": tax_account,
                "payable": tax_group.tax_payable_account_id,
                "receivable": tax_group.tax_receivable_account_id,
            }

            test_tax = self._add_basic_tax_for_report(
                tax_unit_report,
                42,
                "sale",
                tax_group,
                [(100, tax_account, True)],
                company=company,
            )
            created_taxes[company] = test_tax
            tax_accounts[company] = tax_account

            # Create an invoice with this tax
            self.init_invoice(
                "out_invoice",
                partner=self.partner_a,
                invoice_date=invoice_date,
                post=True,
                amounts=[100 * (index + 1)],
                taxes=test_tax,
                company=company,
            )

        # Check report content, with various scenarios of active companies
        for active_companies in (
            company_1,
            company_2,
            company_3,
            unit_companies,
            all_companies,
            company_2 + company_3,
        ):
            # In the regular flow, selected companies are changed from the selector, in the UI.
            # The tax unit option of the report changes the value of the selector, so it'll
            # always stay consistent with allowed_company_ids.
            options = self._generate_options(
                tax_unit_report.with_context(allowed_company_ids=active_companies.ids),
                invoice_date,
                invoice_date,
            )

            target_unit = tax_unit if company_3 != active_companies[0] else None
            self.assertTrue(
                (not target_unit and not options["available_tax_units"])
                or (
                    options["available_tax_units"]
                    and any(
                        available_unit["id"] == target_unit.id
                        for available_unit in options["available_tax_units"]
                    )
                ),
                "The tax unit should always be available when self.env.company is part of it.",
            )

            self.assertEqual(
                options["tax_unit"] != "company_only",
                active_companies == unit_companies,
                "The tax unit option should only be enabled when all the companies of the unit are selected, and nothing else.",
            )

            self.assertLinesValues(
                tax_unit_report.with_context(
                    allowed_company_ids=active_companies.ids
                )._get_lines(options),
                #   Name                                                          Balance
                [0, 1],
                [
                    # Company 1
                    (
                        f"{created_taxes[company_1].id}-invoice-base",
                        100 if company_1 in active_companies else 0.0,
                    ),
                    (
                        f"{created_taxes[company_1].id}-invoice-100",
                        42 if company_1 in active_companies else 0.0,
                    ),
                    (f"{created_taxes[company_1].id}-refund-base", 0.0),
                    (f"{created_taxes[company_1].id}-refund-100", 0.0),
                    # Company 2
                    (
                        f"{created_taxes[company_2].id}-invoice-base",
                        200
                        if active_companies == unit_companies
                        or active_companies[0] == company_2
                        else 0.0,
                    ),
                    (
                        f"{created_taxes[company_2].id}-invoice-100",
                        84
                        if active_companies == unit_companies
                        or active_companies[0] == company_2
                        else 0.0,
                    ),
                    (f"{created_taxes[company_2].id}-refund-base", 0.0),
                    (f"{created_taxes[company_2].id}-refund-100", 0.0),
                    # Company 3 (not part of the unit, so always 0 in our cases)
                    (
                        f"{created_taxes[company_3].id}-invoice-base",
                        300 if company_3 == active_companies[0] else 0.0,
                    ),
                    (
                        f"{created_taxes[company_3].id}-invoice-100",
                        126 if company_3 == active_companies[0] else 0.0,
                    ),
                    (f"{created_taxes[company_3].id}-refund-base", 0.0),
                    (f"{created_taxes[company_3].id}-refund-100", 0.0),
                ],
                options,
            )

        # Test tax closing for the tax unit
        self._assert_tax_closing(
            company_1,
            "2018-01-01",
            "2018-03-31",
            self.domestic_tax_return_type,
            {
                company_1: [
                    {
                        "debit": 42.0,
                        "credit": 0.0,
                        "account_id": tax_accounts_map[company_1]["tax"].id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 42.0,
                        "account_id": tax_accounts_map[company_1]["payable"].id,
                    },
                ],
                company_2: [
                    {
                        "debit": 84,
                        "credit": 0.0,
                        "account_id": tax_accounts_map[company_2]["tax"].id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 84.0,
                        "account_id": tax_accounts_map[company_2]["payable"].id,
                    },
                ],
            },
            tax_unit=tax_unit,
        )

    def test_tax_unit_create_horizontal_group(self):
        """Creating two tax units must create the matching horizontal groups and link them to the generic tax report."""
        company_1 = self.company_data["company"]
        company_2 = self.company_data_2["company"]
        company_2.currency_id = company_1.currency_id
        unit_companies_1 = company_1 + company_2

        company_3 = self.setup_other_company(name="Company 3")["company"]
        company_4 = self.setup_other_company(name="Company 4")["company"]
        unit_companies_2 = company_3 + company_4

        self.env["account.tax.unit"].create(
            [
                {
                    "name": "First Tax Unit",
                    "country_id": self.fiscal_country.id,
                    "vat": "DW1234567890",
                    "company_ids": [Command.set(unit_companies_1.ids)],
                    "main_company_id": company_1.id,
                },
                {
                    "name": "Second Tax Unit",
                    "country_id": self.fiscal_country.id,
                    "vat": "DW1234567890",
                    "company_ids": [Command.set(unit_companies_2.ids)],
                    "main_company_id": company_3.id,
                },
            ]
        )

        # Check if the two last horizontal_group are the one created from the tax unit
        horizontal_groups = self.env["account.report.horizontal.group"].search([])[-2:]
        self.assertEqual(
            ["First Tax Unit", "Second Tax Unit"], horizontal_groups.mapped("name")
        )

        # Check if the generic_tax_report has the two groups
        generic_tax_report = self.env.ref("account.generic_tax_report")
        self.assertTrue(
            all(
                horizontal_group_id in generic_tax_report.horizontal_group_ids.ids
                for horizontal_group_id in horizontal_groups.ids
            )
        )

    def test_tax_unit_auto_fiscal_position(self):
        # setup companies
        company_1 = self.company_data["company"]
        company_2 = self.company_data_2["company"]
        company_2.currency_id = company_1.currency_id
        company_3 = self.setup_other_company(name="Company 3")["company"]
        company_4 = self.setup_other_company(name="Company 4")["company"]
        unit_companies = company_1 + company_2 + company_3
        all_companies = unit_companies + company_4

        # create a tax unit containing 3 companies
        tax_unit = self.env["account.tax.unit"].create(
            {
                "name": "One unit to rule them all",
                "country_id": self.fiscal_country.id,
                "vat": "DW1234567890",
                "company_ids": [Command.set(unit_companies.ids)],
                "main_company_id": company_1.id,
            }
        )
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        for current_company in unit_companies:
            # verify that partners for other companies in the unit have a fiscal position that removes taxes
            created_fp = tax_unit._get_tax_unit_fiscal_positions(
                companies=current_company
            )
            self.assertTrue(created_fp)
            self.assertEqual(
                (unit_companies - current_company)
                .partner_id.with_company(current_company)
                .property_account_position_id,
                created_fp,
            )
            # Tax unit FP drops taxes bound to a fiscal position; taxes
            # without fiscal_position_ids are preserved by design.
            company_taxes = self.env["account.tax"].search(
                [("company_ids", "in", [current_company.id])]
            )
            bound_taxes = company_taxes.filtered("fiscal_position_ids")
            all_taxes = company_taxes - bound_taxes
            self.assertFalse(created_fp.map_tax(bound_taxes))
            self.assertEqual(created_fp.map_tax(all_taxes), all_taxes)
            self.assertFalse(
                current_company.partner_id.with_company(
                    current_company
                ).property_account_position_id
            )
        tax_unit._compute_fpos_synced()
        self.assertTrue(tax_unit.fpos_synced)

        # remove company 3 from the unit and verify that the fiscal positions are removed from the relevant companies
        tax_unit.write({"company_ids": [Command.unlink(company_3.id)]})
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertFalse(
            company_3.partner_id.with_company(company_1).property_account_position_id
        )
        self.assertFalse(
            company_1.partner_id.with_company(company_3).property_account_position_id
        )
        company_1_fp = tax_unit._get_tax_unit_fiscal_positions(companies=company_1)
        self.assertEqual(
            company_2.partner_id.with_company(company_1).property_account_position_id,
            company_1_fp,
        )
        self.assertTrue(tax_unit.fpos_synced)

        # add company 3, remove company 2
        tax_unit.write(
            {"company_ids": [Command.link(company_3.id), Command.unlink(company_2.id)]}
        )
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        company_1_fp = tax_unit._get_tax_unit_fiscal_positions(companies=company_1)
        self.assertEqual(
            company_3.partner_id.with_company(company_1).property_account_position_id,
            company_1_fp,
        )
        self.assertFalse(
            company_2.partner_id.with_company(company_1).property_account_position_id
        )
        self.assertTrue(
            company_1.partner_id.with_company(company_3).property_account_position_id
        )

        # remove the fiscal position from the partner of company 1
        company_1.partner_id.with_company(
            company_3
        ).property_account_position_id = False
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertTrue(tax_unit.fpos_synced)

        # replace all companies
        tax_unit.write(
            {
                "company_ids": [Command.set([company_2.id, company_4.id])],
                "main_company_id": company_2.id,
            }
        )
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertTrue(tax_unit.fpos_synced)

        # no fiscal positions should exist after deleting the unit
        tax_unit.unlink()
        for company in all_companies:
            self.assertFalse(
                all_companies.partner_id.with_company(
                    company
                ).property_account_position_id
            )

    def test_tax_unit_with_foreign_vat_fpos(self):
        # Company 1 has the test country as domestic country, and a foreign VAT fpos in a different province
        company_1 = self.company_data["company"]

        # Company 2 belongs to a different country, and has a foreign VAT fpos to the test country
        company_2 = self.company_data_2["company"]
        company_2.currency_id = company_1.currency_id

        self.env["account.fiscal.position"].create(
            {
                "name": "fpos",
                "foreign_vat": "tagada tsoin tsoin",
                "country_id": self.fiscal_country.id,
                "company_id": company_2.id,
                "auto_apply": True,
            }
        )

        self.partner_a.country_id = self.fiscal_country.id

        company_2_tax_account = self.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "comp.2.tax",
                "account_type": "liability_current",
                "company_ids": company_2.ids,
            }
        )
        company_2_tax_group = self._instantiate_basic_test_tax_group(
            company=company_2, country=self.fiscal_country
        )
        company_2_tax = self._add_basic_tax_for_report(
            self.domestic_tax_report,
            11,
            "sale",
            company_2_tax_group,
            [(100, company_2_tax_account, True)],
            company=company_2,
        )
        self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            invoice_date="2021-02-02",
            post=True,
            amounts=[1000],
            taxes=company_2_tax,
            company=company_2,
        )

        # Both companies belong to a tax unit in test country
        tax_unit = self.env["account.tax.unit"].create(
            {
                "name": "Taxvengers, assemble!",
                "country_id": self.fiscal_country.id,
                "vat": "dudu",
                "company_ids": [Command.set((company_1 + company_2).ids)],
                "main_company_id": company_1.id,
            }
        )

        # Opening the tax report for test country, we should see the same as in
        # test_tax_report_domestic_monocompany + the 1000 of company 2, whatever the main company

        # Varying the order of the two companies (and hence changing the "main" active one) should make no difference.
        for unit_companies in ((company_1 + company_2), (company_2 + company_1)):
            options = self._generate_options(
                self.domestic_tax_report.with_context(
                    allowed_company_ids=unit_companies.ids
                ),
                "2021-01-01",
                "2021-03-31",
            )

            self.assertEqual(
                options["tax_unit"],
                tax_unit.id,
                "The tax unit should have been auto-detected.",
            )

            self.assertLinesValues(
                self.domestic_tax_report._get_lines(options),
                #   Name                                                          Balance
                [0, 1],
                [
                    # out_invoice
                    (f"{self.domestic_sale_tax.id}-invoice-base", 200),
                    (f"{self.domestic_sale_tax.id}-invoice-30", 30),
                    (f"{self.domestic_sale_tax.id}-invoice-70", 70),
                    (f"{self.domestic_sale_tax.id}-invoice--100", -100),
                    # out_refund
                    (f"{self.domestic_sale_tax.id}-refund-base", -20),
                    (f"{self.domestic_sale_tax.id}-refund-30", -3),
                    (f"{self.domestic_sale_tax.id}-refund-70", -7),
                    (f"{self.domestic_sale_tax.id}-refund--100", 10),
                    # in_invoice
                    (f"{self.domestic_purchase_tax.id}-invoice-base", 400),
                    (f"{self.domestic_purchase_tax.id}-invoice-40", 80),
                    (f"{self.domestic_purchase_tax.id}-invoice-60", 120),
                    (f"{self.domestic_purchase_tax.id}-invoice--100", -200),
                    # in_refund
                    (f"{self.domestic_purchase_tax.id}-refund-base", -60),
                    (f"{self.domestic_purchase_tax.id}-refund-40", -12),
                    (f"{self.domestic_purchase_tax.id}-refund-60", -18),
                    (f"{self.domestic_purchase_tax.id}-refund--100", 30),
                    # out_invoice, company 2
                    (f"{company_2_tax.id}-invoice-base", 1000),
                    (f"{company_2_tax.id}-invoice-100", 110),
                    # out_refund, company 2
                    (f"{company_2_tax.id}-refund-base", 0),
                    (f"{company_2_tax.id}-refund-100", 0),
                ],
                options,
            )

        self._assert_tax_closing(
            company_1,
            "2021-01-01",
            "2021-03-31",
            self.domestic_tax_return_type,
            {
                company_1: [
                    # 0.5 * 0.7 * (200 - 20) = 63
                    {"debit": 63.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                    # 0.5 * 0.6 * (400 - 60) = 102
                    {
                        "debit": 0.0,
                        "credit": 102.0,
                        "account_id": self.tax_account_1.id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 63.0,
                        "account_id": self.tax_group_1.tax_payable_account_id.id,
                    },
                    {
                        "debit": 102.0,
                        "credit": 0.0,
                        "account_id": self.tax_group_2.tax_receivable_account_id.id,
                    },
                ],
                company_2: [
                    # 0.11 * 1 * 1000 = 110
                    {
                        "debit": 110.0,
                        "credit": 0.0,
                        "account_id": company_2_tax_account.id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 110.0,
                        "account_id": company_2_tax_group.tax_payable_account_id.id,
                    },
                ],
            },
            tax_unit=tax_unit,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_tax_report_with_entries_with_sale_and_purchase_taxes(self):
        """Ensure signs are managed properly for entry moves, in the case where
        invoice/bill like entries are created and reverted.
        """
        today = fields.Date.today()
        company = self.env.user.company_id
        tax_report = self.env["account.report"].create(
            {
                "name": "Test",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )

        # We create some report lines
        report_lines_dict = {
            "sale": [
                self._create_tax_report_line(
                    "Sale base", tax_report, sequence=1, tag_name="-sale_b"
                ),
                self._create_tax_report_line(
                    "Sale tax", tax_report, sequence=1, tag_name="-sale_t"
                ),
            ],
            "purchase": [
                self._create_tax_report_line(
                    "Purchase base", tax_report, sequence=2, tag_name="purchase_b"
                ),
                self._create_tax_report_line(
                    "Purchase tax", tax_report, sequence=2, tag_name="purchase_t"
                ),
            ],
        }

        # We create a sale and a purchase tax, linked to our report line tags
        taxes = self._create_taxes_for_report_lines(report_lines_dict, company)

        account_types = {
            "sale": "income",
            "purchase": "expense",
        }
        for tax in taxes:
            account = self.env["account.account"].search(
                [
                    ("company_ids", "=", company.id),
                    ("account_type", "=", account_types[tax.type_tax_use]),
                ],
                limit=1,
            )
            # create one entry and it's reverse
            move_form = Form(
                self.env["account.move"].with_context(default_move_type="entry")
            )
            with move_form.line_ids.new() as line:
                line.account_id = account
                if tax.type_tax_use == "sale":
                    line.credit = 1000
                else:
                    line.debit = 1000
                line.tax_ids.clear()
                line.tax_ids.add(tax)

            # Create a third account.move.line for balance.
            with move_form.line_ids.new() as line:
                line.account_id = account
                if tax.type_tax_use == "sale":
                    line.debit = 1200
                else:
                    line.credit = 1200
            move = move_form.save()
            move.action_post()
            refund_wizard = (
                self.env["account.move.reversal"]
                .with_context(active_model="account.move", active_ids=move.ids)
                .create(
                    {
                        "reason": "reasons",
                        "journal_id": self.company_data["default_journal_misc"].id,
                    }
                )
            )
            refund_wizard.modify_moves()

            self.assertEqual(
                move.line_ids.tax_repartition_line_id,
                move.reversal_move_ids.line_ids.tax_repartition_line_id,
                "The same repartition line should be used when reverting a misc operation, to ensure they sum up to 0 in all cases.",
            )

        options = self._generate_options(tax_report, today, today)

        # We check the taxes on entries have impacted the report properly
        inv_report_lines = tax_report._get_lines(options)

        self.assertLinesValues(
            inv_report_lines,
            #   Name                         Balance
            [0, 1],
            [
                ("Sale base", 0.0),
                ("Sale tax", 0.0),
                ("Purchase base", 0.0),
                ("Purchase tax", 0.0),
            ],
            options,
        )

    @freeze_time("2023-10-05 02:00:00")
    def test_invoice_like_entry_reverse_caba_report(self):
        """Cancelling the reconciliation of an invoice using cash basis taxes should reverse the cash basis move
        in such a way that the original cash basis move lines' impact falls down to 0.
        """
        self.env.company.account_config_id.tax_exigibility = True

        tax_report = self.env["account.report"].create(
            {
                "name": "CABA test",
                "country_id": self.fiscal_country.id,
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
            }
        )
        report_line_invoice_base = self._create_tax_report_line(
            "Invoice base", tax_report, sequence=1, tag_name="-caba_invoice_base"
        )
        report_line_invoice_tax = self._create_tax_report_line(
            "Invoice tax", tax_report, sequence=2, tag_name="-caba_invoice_tax"
        )
        report_line_refund_base = self._create_tax_report_line(
            "Refund base", tax_report, sequence=3, tag_name="caba_refund_base"
        )
        report_line_refund_tax = self._create_tax_report_line(
            "Refund tax", tax_report, sequence=4, tag_name="caba_refund_tax"
        )

        tax = self.env["account.tax"].create(
            {
                "name": "The Tax Who Says Ni",
                "type_tax_use": "sale",
                "amount": 42,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": [
                                Command.set(
                                    report_line_invoice_base.expression_ids._get_matching_tags().ids
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "tag_ids": [
                                Command.set(
                                    report_line_invoice_tax.expression_ids._get_matching_tags().ids
                                )
                            ],
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": [
                                Command.set(
                                    report_line_refund_base.expression_ids._get_matching_tags().ids
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "tag_ids": [
                                Command.set(
                                    report_line_refund_tax.expression_ids._get_matching_tags().ids
                                )
                            ],
                        }
                    ),
                ],
            }
        )

        move_form = Form(
            self.env["account.move"]
            .with_company(self.company_data["company"])
            .with_context(default_move_type="entry")
        )
        move_form.date = fields.Date.today()
        with move_form.line_ids.new() as base_line_form:
            base_line_form.name = "Base line"
            base_line_form.account_id = self.company_data["default_account_revenue"]
            base_line_form.credit = 100
            base_line_form.tax_ids.clear()
            base_line_form.tax_ids.add(tax)

        with move_form.line_ids.new() as receivable_line_form:
            receivable_line_form.name = "Receivable line"
            receivable_line_form.account_id = self.company_data[
                "default_account_receivable"
            ]
            receivable_line_form.debit = 142
        move = move_form.save()
        move.action_post()
        # make payment
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 142,
                "date": move.date,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.action_post()

        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [0, 1],
            [
                ("Invoice base", 0.0),
                ("Invoice tax", 0.0),
                ("Refund base", 0.0),
                ("Refund tax", 0.0),
            ],
            report_options,
        )

        # Reconcile the move with a payment
        (payment.move_id + move).line_ids.filtered(
            lambda x: x.account_id == self.company_data["default_account_receivable"]
        ).reconcile()
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [0, 1],
            [
                ("Invoice base", 100),
                ("Invoice tax", 42),
                ("Refund base", 0.0),
                ("Refund tax", 0.0),
            ],
            report_options,
        )

        # Unreconcile the moves
        move.line_ids.remove_move_reconcile()
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [0, 1],
            [
                ("Invoice base", 0.0),
                ("Invoice tax", 0.0),
                ("Refund base", 0.0),
                ("Refund tax", 0.0),
            ],
            report_options,
        )

    def setup_multi_vat_context(self):
        """Setup 2 tax reports, taxes and partner to represent a multiVat context in which both taxes affect both tax report"""

        def get_tag(report_line):
            return report_line.expression_ids._get_matching_tags()

        local_tax_report, foreign_tax_report = self.env["account.report"].create(
            [
                {
                    "name": "The Local Tax Report",
                    "country_id": self.company_data[
                        "company"
                    ].account_config_id.account_fiscal_country_id.id,
                    "root_report_id": self.env.ref("account.generic_tax_report").id,
                    "column_ids": [
                        Command.create(
                            {
                                "name": "balance",
                                "sequence": 1,
                                "expression_label": "balance",
                            }
                        )
                    ],
                },
                {
                    "name": "The Foreign Tax Report",
                    "country_id": self.foreign_country.id,
                    "root_report_id": self.env.ref("account.generic_tax_report").id,
                    "column_ids": [
                        Command.create(
                            {
                                "name": "balance",
                                "sequence": 1,
                                "expression_label": "balance",
                            }
                        )
                    ],
                },
            ]
        )
        local_tax_report_base_line = self._create_tax_report_line(
            "base_local",
            local_tax_report,
            sequence=1,
            code="base_local",
            tag_name="-base_local",
        )
        local_tax_report_tax_line = self._create_tax_report_line(
            "tax_local",
            local_tax_report,
            sequence=2,
            code="tax_local",
            tag_name="-tax_local",
        )
        foreign_tax_report_base_line = self._create_tax_report_line(
            "base_foreign",
            foreign_tax_report,
            sequence=1,
            code="base_foreign",
            tag_name="-base_foreign",
        )
        foreign_tax_report_tax_line = self._create_tax_report_line(
            "tax_foreign",
            foreign_tax_report,
            sequence=2,
            code="tax_foreign",
            tag_name="-tax_foreign",
        )

        local_tax_affecting_foreign_tax_report = self.env["account.tax"].create(
            {"name": "The local tax affecting the foreign report", "amount": 20}
        )
        foreign_tax_affecting_local_tax_report = self.env["account.tax"].create(
            {
                "name": "The foreign tax affecting the local tax report",
                "amount": 20,
                "country_id": self.foreign_country.id,
            }
        )
        for tax in (
            local_tax_affecting_foreign_tax_report,
            foreign_tax_affecting_local_tax_report,
        ):
            base_line, tax_line = tax.invoice_repartition_line_ids
            base_line.tag_ids = get_tag(local_tax_report_base_line) + get_tag(
                foreign_tax_report_base_line
            )
            tax_line.tag_ids = get_tag(local_tax_report_tax_line) + get_tag(
                foreign_tax_report_tax_line
            )
            tax_line.account_id = self.tax_account_1

        local_partner = self.partner_a
        foreign_partner = self.partner_a.copy()
        foreign_partner.country_id = self.foreign_country

        return {
            "tax_report": (
                local_tax_report,
                foreign_tax_report,
            ),
            "taxes": (
                local_tax_affecting_foreign_tax_report,
                foreign_tax_affecting_local_tax_report,
            ),
            "partners": (local_partner, foreign_partner),
        }

    def test_local_tax_can_affect_foreign_tax_report(self):
        setup_data = self.setup_multi_vat_context()
        local_tax_report, foreign_tax_report = setup_data["tax_report"]
        local_tax_affecting_foreign_tax_report, _ = setup_data["taxes"]
        local_partner, _ = setup_data["partners"]

        invoice = self.init_invoice(
            "out_invoice",
            partner=local_partner,
            invoice_date="2022-12-01",
            post=True,
            amounts=[100],
            taxes=local_tax_affecting_foreign_tax_report,
        )
        options = self._generate_options(local_tax_report, "2022-10-01", "2022-12-31")
        self.assertLinesValues(
            local_tax_report._get_lines(options),
            #   Name                                        Balance
            [0, 1],
            [
                ("base_local", 100.0),
                ("tax_local", 20.0),
            ],
            options,
        )

        options = self._generate_options(foreign_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            foreign_tax_report._get_lines(options),
            #   Name                                          Balance
            [0, 1],
            [
                ("base_foreign", 100.0),
                ("tax_foreign", 20.0),
            ],
            options,
        )

    def test_foreign_tax_can_affect_local_tax_report(self):
        setup_data = self.setup_multi_vat_context()
        local_tax_report, foreign_tax_report = setup_data["tax_report"]
        _, foreign_tax_affecting_local_tax_report = setup_data["taxes"]
        _, foreign_partner = setup_data["partners"]

        invoice = self.init_invoice(
            "out_invoice",
            partner=foreign_partner,
            invoice_date="2022-12-01",
            post=True,
            amounts=[100],
            taxes=foreign_tax_affecting_local_tax_report,
        )
        options = self._generate_options(local_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            local_tax_report._get_lines(options),
            #   Name                                        Balance
            [0, 1],
            [
                ("base_local", 100.0),
                ("tax_local", 20.0),
            ],
            options,
        )

        options = self._generate_options(foreign_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            foreign_tax_report._get_lines(options),
            #   Name                                          Balance
            [0, 1],
            [
                ("base_foreign", 100.0),
                ("tax_foreign", 20.0),
            ],
            options,
        )

    def test_tax_report_w_rounding_line(self):
        """Check that the tax report is correct when a rounding line is added to an invoice."""
        self.env["res.config.settings"].create(
            {"company_id": self.company_data["company"].id, "group_cash_rounding": True}
        )

        rounding = self.env["account.cash.rounding"].create(
            {
                "name": "Test rounding",
                "rounding": 0.05,
                "strategy": "biggest_tax",
                "rounding_method": "HALF-UP",
            }
        )

        tax = self.sale_tax_percentage_incl_1.copy(
            {
                "name": "The Tax Who Says Ni",
                "amount": 21,
            }
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "The Holy Grail",
                            "quantity": 1,
                            "price_unit": 1.26,
                            "tax_ids": [
                                Command.set(self.sale_tax_percentage_incl_1.ids)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "What is your favourite colour?",
                            "quantity": 1,
                            "price_unit": 2.32,
                            "tax_ids": [Command.set(tax.ids)],
                        }
                    ),
                ],
                "invoice_cash_rounding_id": rounding.id,
            }
        )

        invoice.action_post()

        self.assertRecordValues(
            invoice.line_ids,
            [
                {
                    "name": "The Holy Grail",
                    "debit": 0.00,
                    "credit": 1.05,
                },
                {
                    "name": "What is your favourite colour?",
                    "debit": 0.00,
                    "credit": 1.92,
                },
                {
                    "name": self.sale_tax_percentage_incl_1.name,
                    "debit": 0.00,
                    "credit": 0.21,
                },
                {
                    "name": tax.name,
                    "debit": 0.00,
                    "credit": 0.40,
                },
                {
                    "name": f"{tax.name} (rounding)",
                    "debit": 0.00,
                    "credit": 0.02,
                },
                {
                    "name": invoice.name,
                    "debit": 3.60,
                    "credit": 0.00,
                },
            ],
        )

        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice.date, invoice.date)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                         Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 0.63),
                (
                    f"{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)",
                    1.05,
                    0.21,
                ),
                (f"{tax.name} ({tax.amount}%)", 1.92, 0.42),
                ("Total Sales", "", 0.63),
            ],
            options,
        )

        report = self.env.ref("account.generic_tax_report_account_tax")
        options["report_id"] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                         Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 0.63),
                (self.company_data["default_account_revenue"].display_name, "", 0.63),
                (
                    f"{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)",
                    1.05,
                    0.21,
                ),
                (f"{tax.name} ({tax.amount}%)", 1.92, 0.42),
                (
                    f"Total {self.company_data['default_account_revenue'].display_name}",
                    "",
                    0.63,
                ),
                ("Total Sales", "", 0.63),
            ],
            options,
        )

        report = self.env.ref("account.generic_tax_report_tax_account")
        options["report_id"] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                               Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 0.63),
                (
                    f"{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)",
                    "",
                    0.21,
                ),
                (self.company_data["default_account_revenue"].display_name, 1.05, 0.21),
                (
                    f"Total {self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)",
                    "",
                    0.21,
                ),
                (f"{tax.name} ({tax.amount}%)", "", 0.42),
                (self.company_data["default_account_revenue"].display_name, 1.92, 0.42),
                (f"Total {tax.name} ({tax.amount}%)", "", 0.42),
                ("Total Sales", "", 0.63),
            ],
            options,
        )

    def test_multivat_multi_fpos(self):
        """Tests the tax report and closing in a multivat setup, with multiple foreign VAT fiscal positions defined for the same country, with
        the same VAT number, ensuring all of them are properly taken into account.
        """
        self.foreign_vat_fpos.auto_apply = False
        self.env["account.fiscal.position"].create(
            {
                "name": "Another test fpos",
                "auto_apply": True,
                "country_id": self.foreign_vat_fpos.country_id.id,
                "foreign_vat": self.foreign_vat_fpos.foreign_vat,
            }
        )

        self.init_invoice(
            "out_invoice",
            partner=self.test_fpos_foreign_partner,
            invoice_date="2021-01-01",
            post=True,
            amounts=[100],
            taxes=self.foreign_sale_tax,
        )

        options = self._generate_options(
            self.foreign_tax_report, "2021-01-01", "2021-03-31"
        )

        self.assertLinesValues(
            self.foreign_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0, 1],
            [
                # out_invoice
                (f"{self.foreign_sale_tax.id}-invoice-base", 900),
                (f"{self.foreign_sale_tax.id}-invoice-80", 432),
                (f"{self.foreign_sale_tax.id}-invoice-20", 108),
                (f"{self.foreign_sale_tax.id}-invoice--100", -540),
                # out_refund
                (f"{self.foreign_sale_tax.id}-refund-base", -200),
                (f"{self.foreign_sale_tax.id}-refund-80", -96),
                (f"{self.foreign_sale_tax.id}-refund-20", -24),
                (f"{self.foreign_sale_tax.id}-refund--100", 120),
                # in_invoice
                (f"{self.foreign_purchase_tax.id}-invoice-base", 1000),
                (f"{self.foreign_purchase_tax.id}-invoice-51", 306),
                (f"{self.foreign_purchase_tax.id}-invoice-49", 294),
                (f"{self.foreign_purchase_tax.id}-invoice--100", -600),
                # in_refund
                (f"{self.foreign_purchase_tax.id}-refund-base", -600),
                (f"{self.foreign_purchase_tax.id}-refund-51", -183.6),
                (f"{self.foreign_purchase_tax.id}-refund-49", -176.4),
                (f"{self.foreign_purchase_tax.id}-refund--100", 360),
            ],
            options,
        )

        self._assert_tax_closing(
            self.env.company,
            "2021-01-01",
            "2021-03-31",
            self.foreign_tax_return_type,
            {
                self.env.company: [
                    # 0.6 * 0.2 * (800 - 200 + 100) = 84
                    {"debit": 84.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                    # 0.6 * 0.49 * (1000 - 600) = 117.6
                    {
                        "debit": 0.0,
                        "credit": 117.6,
                        "account_id": self.tax_account_1.id,
                    },
                    {
                        "debit": 0.0,
                        "credit": 84.0,
                        "account_id": self.tax_group_3.tax_payable_account_id.id,
                    },
                    {
                        "debit": 117.6,
                        "credit": 0.0,
                        "account_id": self.tax_group_4.tax_receivable_account_id.id,
                    },
                ],
            },
        )

    def test_multiple_same_tax_lines_with_multiple_analytics(self):
        """One Invoice line with analytic_distribution and another with another analytic_distribution, both with the same tax"""
        analytic_plan = self.env["account.analytic.plan"].create(
            {"name": "Plan with Tax details"}
        )
        analytic_account_1 = self.env["account.analytic.account"].create(
            {
                "name": "Analytic account with Tax details",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        analytic_account_2 = self.env["account.analytic.account"].create(
            {
                "name": " testAnalytic account",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        tax_10 = self.env["account.tax"].create(
            {
                "name": "tax_10",
                "amount_type": "percent",
                "amount": 10.0,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line1",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 200.0,
                            "tax_ids": [Command.set(tax_10.ids)],
                            "analytic_distribution": {
                                analytic_account_1.id: 100,
                            },
                        }
                    ),
                    Command.create(
                        {
                            "name": "line2",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 100.0,
                            "tax_ids": [Command.set(tax_10.ids)],
                            "analytic_distribution": {
                                analytic_account_2.id: 100,
                            },
                        }
                    ),
                ],
            }
        )
        invoice.action_post()
        invoice2 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line1",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 10.0,
                            "tax_ids": [Command.set(tax_10.ids)],
                            "analytic_distribution": {
                                analytic_account_2.id: 100,
                            },
                        }
                    ),
                ],
            }
        )
        invoice2.action_post()

        self.assertRecordValues(
            invoice.line_ids,
            [
                {"name": "line1", "debit": 0.00, "credit": 200.0},
                {"name": "line2", "debit": 0.00, "credit": 100.0},
                {"name": tax_10.name, "debit": 0.00, "credit": 20.0},
                {"name": tax_10.name, "debit": 0.00, "credit": 10.0},
                {"name": invoice.name, "debit": 330.0, "credit": 0.00},
            ],
        )

        self.assertRecordValues(
            invoice2.line_ids,
            [
                {"name": "line1", "debit": 0.00, "credit": 10.0},
                {"name": tax_10.name, "debit": 0.00, "credit": 1.0},
                {"name": invoice2.name, "debit": 11.0, "credit": 0.00},
            ],
        )

        report = self.env.ref("account.generic_tax_report_account_tax")
        options = self._generate_options(report, invoice.date, invoice.date)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                          Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 31.0),
                (self.company_data["default_account_revenue"].display_name, "", 31.0),
                (f"{tax_10.name} ({tax_10.amount}%)", 310.0, 31.0),
                (
                    f"Total {self.company_data['default_account_revenue'].display_name}",
                    "",
                    31.0,
                ),
                ("Total Sales", "", 31.0),
            ],
            options,
        )

        report = self.env.ref("account.generic_tax_report_tax_account")
        options["report_id"] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                           Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 31.0),
                (f"{tax_10.name} ({tax_10.amount}%)", "", 31.0),
                (
                    self.company_data["default_account_revenue"].display_name,
                    310.0,
                    31.0,
                ),
                (f"Total {tax_10.name} ({tax_10.amount}%)", "", 31.0),
                ("Total Sales", "", 31.0),
            ],
            options,
        )

    def test_caba_negative_lines_with_multiple_accounts(self):
        """One invoice with 2 lines on 2 income accounts, one with a negative total, both with a caba tax."""
        self.company_data["company"].account_config_id.tax_exigibility = True
        account_1 = self.company_data["default_account_revenue"]
        account_2 = self.company_data["default_account_assets"]
        caba_tax_10 = self.env["account.tax"].create(
            {
                "name": "tax_10",
                "amount_type": "percent",
                "type_tax_use": "sale",
                "amount": 10.0,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line1",
                            "account_id": account_1.id,
                            "price_unit": -1000.0,
                            "tax_ids": [Command.set(caba_tax_10.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "name": "line2",
                            "account_id": account_2.id,
                            "price_unit": 2000.0,
                            "tax_ids": [Command.set(caba_tax_10.ids)],
                        }
                    ),
                ],
            }
        )
        invoice.action_post()

        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 1100,
                "date": invoice.date,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.action_post()

        # Reconcile the move with a payment
        (payment.move_id + invoice).line_ids.filtered(
            lambda x: x.account_id == self.company_data["default_account_receivable"]
        ).reconcile()

        report = self.env.ref("account.generic_tax_report_account_tax")
        options = self._generate_options(report, invoice.date, invoice.date)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                          Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 100.0),
                (account_2.display_name, "", 200.0),
                (f"{caba_tax_10.name} ({caba_tax_10.amount}%)", 2000.0, 200.0),
                (f"Total {account_2.display_name}", "", 200.0),
                (account_1.display_name, "", -100.0),
                (f"{caba_tax_10.name} ({caba_tax_10.amount}%)", -1000.0, -100.0),
                (f"Total {account_1.display_name}", "", -100.0),
                ("Total Sales", "", 100.0),
            ],
            options,
        )

        report = self.env.ref("account.generic_tax_report_tax_account")
        options["report_id"] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                           Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 100.0),
                (f"{caba_tax_10.name} ({caba_tax_10.amount}%)", "", 100.0),
                (account_2.display_name, 2000.0, 200.0),
                (account_1.display_name, -1000.0, -100.0),
                (f"Total {caba_tax_10.name} ({caba_tax_10.amount}%)", "", 100.0),
                ("Total Sales", "", 100.0),
            ],
            options,
        )

    def test_caba_not_duplicated_in_tax_report_when_in_tax_group(self):
        """
        Test that the CABA tax amount is not duplicated in the general tax report
        when it is part of a tax group.
        """

        self.env.company.account_config_id.tax_exigibility = True

        regular_tax = self.env["account.tax"].create(
            {
                "name": "Regular",
                "amount": 10,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )

        caba_tax = self.env["account.tax"].create(
            {
                "name": "Cash Basis",
                "amount": 10,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
            }
        )

        tax_group = self.env["account.tax"].create(
            {
                "name": "tax_group",
                "amount_type": "group",
                "children_tax_ids": [Command.set((regular_tax + caba_tax).ids)],
            }
        )

        invoice = self.init_invoice(
            "out_invoice",
            invoice_date="2026-01-01",
            post=True,
            amounts=[100],
            taxes=tax_group,
            company=self.company_data["company"],
        )

        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice.date, invoice.date)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                           Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 10.0),
                (f"{regular_tax.name} ({regular_tax.amount}%)", 100.0, 10.0),
                ("Total Sales", "", 10.0),
            ],
            options,
        )

        self._register_full_payment_for_invoice(invoice)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                           Base      Tax
            [0, 1, 2],
            [
                ("Sales", "", 20.0),
                (f"{regular_tax.name} ({regular_tax.amount}%)", 100.0, 10.0),
                (f"{caba_tax.name} ({caba_tax.amount}%)", 100.0, 10.0),
                ("Total Sales", "", 20.0),
            ],
            options,
        )

    def test_previous_return_period_date_scope(self):
        self.init_invoice(
            "in_invoice", invoice_date="2024-09-30", post=True, amounts=[60]
        )
        self.init_invoice(
            "in_invoice", invoice_date="2024-12-31", post=True, amounts=[42]
        )
        self.init_invoice(
            "in_invoice", invoice_date="2025-01-01", post=True, amounts=[100]
        )

        report = self.env["account.report"].create(
            {
                "name": "Test report",
                "column_ids": [
                    Command.create(
                        {
                            "name": "Balance",
                            "sequence": 1,
                            "expression_label": "balance",
                        }
                    )
                ],
                "line_ids": [
                    Command.create(
                        {
                            "name": "test",
                            "expression_ids": [
                                Command.create(
                                    {
                                        "label": "balance",
                                        "engine": "domain",
                                        "formula": [
                                            ("account_id.account_type", "=", "expense")
                                        ],
                                        "subformula": "sum",
                                        "date_scope": "previous_return_period",
                                    }
                                )
                            ],
                        }
                    ),
                ],
            }
        )

        self.env["account.return.type"].create(
            {
                "name": "TestReturn",
                "report_id": report.id,
                "deadline_periodicity": "trimester",
                "deadline_start_date": "2020-01-01",
            }
        )

        options = self._generate_options(report, "2025-01-01", "2025-03-31")
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Balance
            [0, 1],
            [
                ("test", 42.0),
            ],
            options,
        )

        options = self._generate_options(report, "2025-01-01", "2025-01-31")
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Balance
            [0, 1],
            [
                ("test", 42.0),
            ],
            options,
        )

        options = self._generate_options(report, "2025-02-01", "2025-02-28")
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Balance
            [0, 1],
            [
                ("test", 42.0),
            ],
            options,
        )

        options = self._generate_options(report, "2025-03-01", "2025-03-31")
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Balance
            [0, 1],
            [
                ("test", 42.0),
            ],
            options,
        )

        options = self._generate_options(report, "2025-04-01", "2025-04-01")
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Balance
            [0, 1],
            [
                ("test", 100.0),
            ],
            options,
        )
