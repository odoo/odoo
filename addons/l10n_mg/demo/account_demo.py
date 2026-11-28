import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("mg", "res.company", demo=True)
    def _get_mg_demo_data_res_company(self) -> dict:
        # Start the accounting at the beginning of the year of the demo entries, so that their returns exist
        return {
            self.env.company.id: {
                "account_opening_date": self._get_mg_demo_period().replace(
                    month=1,
                    day=1,
                ),
            },
        }

    @template("mg", "res.partner", demo=True)
    def _get_mg_demo_data_res_partner(self) -> dict:
        company = self.env.company
        local = {
            "country_id": "base.mg",
            "company_id": company.id,
            "city": "Antananarivo",
        }
        return {
            "mg_partner_demo_customer": {
                **local,
                "name": "Société Malgache de Négoce",
                "is_company": True,
                "street": "Lot IVG 12, Behoririka",
                "vat": "4000123456",
                "additional_identifiers": {
                    "MG_NIF": "4000123456",
                    "MG_STAT": "46901112009000111",
                },
            },
            "mg_partner_demo_supplier": {
                **local,
                "name": "Fournitures Ankorondrano SARL",
                "is_company": True,
                "street": "Rue Ravoninahitriniarivo, Ankorondrano",
                "vat": "4000654321",
                "additional_identifiers": {
                    "MG_NIF": "4000654321",
                    "MG_STAT": "46521112012000222",
                },
            },
            "mg_partner_demo_public_buyer": {
                **local,
                "name": "Commune Demo de Madagascar",
                "is_company": True,
                "street": "Place de l'Hôtel de Ville",
                "vat": "4000111222",
                "additional_identifiers": {"MG_NIF": "4000111222"},
            },
            "mg_partner_demo_customs": {
                **local,
                "name": "Bureau des Douanes Demo",
                "is_company": True,
                "street": "Port de Toamasina",
                "city": "Toamasina",
                "vat": "4000333444",
                "additional_identifiers": {"MG_NIF": "4000333444"},
            },
            "mg_partner_demo_base_producer": {
                **local,
                "name": "Rakotomalala Hery (vanilla producer)",
                "is_company": False,
                "street": "Fokontany Ambodivoara",
                "city": "Sambava",
            },
            "mg_partner_demo_foreign_customer": {
                "name": "Comptoir Océan Indien SAS",
                "is_company": True,
                "company_id": company.id,
                "country_id": "base.fr",
                "street": "12 Quai de la Joliette",
                "city": "Marseille",
                "zip": "13002",
            },
            "mg_partner_demo_nonresident_provider": {
                "name": "Indian Ocean Consulting Ltd",
                "is_company": True,
                "company_id": company.id,
                "country_id": "base.mu",
                "street": "Cybercity Tower 1",
                "city": "Ebène",
            },
        }

    @template("mg", "account.move", demo=True)
    def _get_mg_demo_data_move(self) -> dict:
        if self.env.company.l10n_mg_tax_regime == "is":
            moves = self._get_mg_demo_data_move_is()
        else:
            moves = self._get_mg_demo_data_move_ir()
        return {self.company_xmlid(xmlid): values for xmlid, values in moves.items()}

    def _post_load_demo_data(self, template_code: str) -> None:
        super()._post_load_demo_data(template_code)
        if template_code != "mg":
            return
        moves = self.env["account.move"]
        for xmlid in self._get_mg_demo_move_xmlids():
            moves |= self.ref(xmlid, raise_if_not_found=False)
        for move in moves.sorted("date"):
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception("Error while posting the Malagasy demo data")

    def _get_mg_demo_move_xmlids(self) -> list[str]:
        moves = (
            self._get_mg_demo_data_move_is()
            if self.env.company.l10n_mg_tax_regime == "is"
            else self._get_mg_demo_data_move_ir()
        )
        return list(moves)

    def _get_mg_demo_period(self) -> date:
        """The demo entries are booked in the previous month, whose monthly returns are due this month."""
        return fields.Date.context_today(self) - relativedelta(months=1)

    def _get_mg_demo_invoice(
        self,
        move_type: str,
        partner: str,
        day: int,
        lines: list[tuple[str, str, float, list[str]]],
        ref: str | None = None,
    ) -> dict:
        invoice_date = self._get_mg_demo_period().replace(day=day)
        values = {
            "move_type": move_type,
            "partner_id": partner,
            "invoice_date": invoice_date,
            "date": invoice_date,
            "invoice_line_ids": [
                Command.create(
                    {
                        "name": name,
                        "account_id": account,
                        "quantity": 1,
                        "price_unit": price_unit,
                        "tax_ids": [Command.set(taxes)],
                    },
                )
                for name, account, price_unit, taxes in lines
            ],
        }
        if ref:
            values["ref"] = ref
        return values

    def _get_mg_demo_salaries(self, gross: float, irsa: float) -> dict:
        """Payroll entry of the month: the IRSA withheld on the salaries feeds the IRSA return."""
        entry_date = self._get_mg_demo_period().replace(day=28)
        return {
            "move_type": "entry",
            "journal_id": "general",
            "date": entry_date,
            "ref": "Salaires du mois",
            "line_ids": [
                Command.create(
                    {
                        "name": "Salaires bruts",
                        "account_id": "mg_account_641",
                        "debit": gross,
                    },
                ),
                Command.create(
                    {
                        "name": "IRSA retenu",
                        "account_id": "mg_account_4421",
                        "credit": irsa,
                    },
                ),
                Command.create(
                    {
                        "name": "Salaires nets à payer",
                        "account_id": "mg_account_421",
                        "credit": gross - irsa,
                    },
                ),
            ],
        }

    def _get_mg_demo_data_move_ir(self) -> dict:
        """Entries of a company under the IR & TVA regime, covering the VAT, intermittent VAT, IRI-NR, synthetic tax
        withheld and IRSA returns."""
        return {
            # VAT return: boxes 01, 06 (20%) and the VAT annex (goods and services)
            "mg_demo_invoice_vat_20": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_customer",
                5,
                [
                    (
                        "Riz de luxe, 50 sacs",
                        "mg_account_707",
                        1_000_000,
                        ["mg_tax_sale_20"],
                    ),
                    (
                        "Installation et formation",
                        "mg_account_706",
                        500_000,
                        ["mg_tax_sale_20"],
                    ),
                ],
            ),
            # VAT return: boxes 02, 07 (butane gas at 10%)
            "mg_demo_invoice_vat_10": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_customer",
                6,
                [
                    (
                        "Bouteilles de gaz butane",
                        "mg_account_707",
                        200_000,
                        ["mg_tax_sale_10"],
                    ),
                ],
            ),
            # VAT return: box 03 (export), foreign client in the VAT annex
            "mg_demo_invoice_export": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_foreign_customer",
                8,
                [
                    (
                        "Vanille Bourbon, 20 kg",
                        "mg_account_707",
                        800_000,
                        ["mg_tax_sale_0_export"],
                    ),
                ],
            ),
            # VAT return: box 04 (exempt operations)
            "mg_demo_invoice_exempt": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_customer",
                9,
                [
                    (
                        "Livres scolaires",
                        "mg_account_707",
                        300_000,
                        ["mg_tax_sale_exempt"],
                    ),
                ],
            ),
            # VAT return: box 05 (market subject to IRM, 8% withheld by the buyer)
            "mg_demo_invoice_market": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_public_buyer",
                10,
                [
                    (
                        "Réfection de la voirie communale",
                        "mg_account_704",
                        2_000_000,
                        ["mg_tax_sale_public_market", "mg_tax_sale_imp_8"],
                    ),
                ],
            ),
            # VAT return: boxes 09, 12 (local goods and services)
            "mg_demo_bill_vat_20": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_supplier",
                11,
                [
                    ("Marchandises", "mg_account_607", 600_000, ["mg_tax_purchase_20"]),
                    (
                        "Maintenance informatique",
                        "mg_account_628",
                        150_000,
                        ["mg_tax_purchase_20"],
                    ),
                ],
                ref="FA-2026-0147",
            ),
            # VAT return: boxes 10, 13 (fixed asset), category I in the VAT annex
            "mg_demo_bill_fixed_asset": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_supplier",
                12,
                [
                    (
                        "Véhicule utilitaire",
                        "mg_account_218",
                        1_500_000,
                        ["mg_tax_purchase_20_fixed"],
                    ),
                ],
                ref="FA-2026-0152",
            ),
            # VAT return: boxes 10, 14 (VAT paid on imports)
            "mg_demo_bill_import": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_customs",
                13,
                [
                    (
                        "TVA à l'importation",
                        "mg_account_607",
                        900_000,
                        ["mg_tax_purchase_20_import"],
                    ),
                ],
                ref="DAU-2026-0042",
            ),
            # VAT return: box 11 (non-deductible VAT)
            "mg_demo_bill_nondeductible": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_supplier",
                14,
                [
                    (
                        "Réception clients",
                        "mg_account_628",
                        100_000,
                        ["mg_tax_purchase_20_nondeductible"],
                    ),
                ],
                ref="FA-2026-0160",
            ),
            # Intermittent VAT (I01, I02), VAT box 15, and IRI-NR (NR01, NR02): services from a non-resident
            "mg_demo_bill_nonresident": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_nonresident_provider",
                15,
                [
                    (
                        "Audit des systèmes d'information",
                        "mg_account_628",
                        1_000_000,
                        ["mg_tax_purchase_20_rc", "mg_tax_ir_nonres_10"],
                    ),
                ],
                ref="IOC-2026-018",
            ),
            # Synthetic tax withheld (IS01, IS02): purchases from a base producer at 5% and 3%
            "mg_demo_bill_base_producer_5": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_base_producer",
                16,
                [
                    (
                        "Vanille verte, 100 kg",
                        "mg_account_601",
                        400_000,
                        ["mg_tax_purchase_is_wh_5"],
                    ),
                ],
                ref="BA-0007",
            ),
            "mg_demo_bill_base_producer_3": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_base_producer",
                17,
                [
                    (
                        "Girofle, 50 kg",
                        "mg_account_601",
                        250_000,
                        ["mg_tax_purchase_is_wh_3"],
                    ),
                ],
                ref="BA-0008",
            ),
            # IRSA return
            "mg_demo_entry_salaries": self._get_mg_demo_salaries(3_000_000, 350_000),
        }

    def _get_mg_demo_data_move_is(self) -> dict:
        """Entries of a company under the Impôt Synthétique, which charges no VAT, covering the synthetic tax,
        synthetic tax withheld and IRSA returns."""
        return {
            # Synthetic tax return: turnover
            "mg_demo_invoice_is_goods": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_customer",
                5,
                [("Produits artisanaux", "mg_account_707", 1_200_000, [])],
            ),
            "mg_demo_invoice_is_services": self._get_mg_demo_invoice(
                "out_invoice",
                "mg_partner_demo_customer",
                12,
                [("Réparations", "mg_account_706", 600_000, [])],
            ),
            # Charges, part of the 2% reduction entered on the synthetic tax return
            "mg_demo_bill_is_supplier": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_supplier",
                14,
                [("Matières premières", "mg_account_601", 300_000, [])],
                ref="FA-2026-0171",
            ),
            # Synthetic tax withheld (IS01, IS02)
            "mg_demo_bill_is_base_producer": self._get_mg_demo_invoice(
                "in_invoice",
                "mg_partner_demo_base_producer",
                16,
                [
                    (
                        "Raphia, 80 kg",
                        "mg_account_601",
                        200_000,
                        ["mg_tax_purchase_is_wh_5"],
                    ),
                ],
                ref="BA-0011",
            ),
            # IRSA return
            "mg_demo_entry_salaries": self._get_mg_demo_salaries(800_000, 60_000),
        }
