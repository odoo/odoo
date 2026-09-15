import io

import xlsxwriter

from odoo import _, http
from odoo.http import request
from odoo.libs.documents import mimetype_for


class AssetTemplateController(http.Controller):
    @http.route(
        "/web/binary/download_asset_template/<int:company_id>", type="http", auth="user"
    )
    def download_template(self, company_id):
        content = self._generate_asset_import_template(company_id)

        return request.prepare_response(
            content,
            headers=[
                (
                    "Content-Type",
                    mimetype_for("xlsx"),
                ),
                (
                    "Content-Disposition",
                    'attachment; filename="asset_import_template.xlsx"',
                ),
            ],
        )

    COLUMN_ORDER = (
        "name",
        "value_original",
        "date_acquisition",
        "asset_group_id",
        "depreciation_method",
        "depreciation_duration",
        "depreciation_period",
        "depreciation_factor",
        "depreciation_prorata",
        "date_prorata",
        "value_depreciated_import",
        "value_salvage",
        "company_id",
        "account_asset_id",
        "account_depreciation_id",
        "account_depreciation_expense_id",
        "depreciation_journal_id",
    )

    EXAMPLES = (
        {
            "name": "Computer 1",
            "value_original": "800.00",
            "date_acquisition": "01-01-2025",
            "depreciation_method": "Straight Line",
            "depreciation_duration": "4",
            "depreciation_period": "Years",
            "depreciation_prorata": "No Prorata",
            "date_prorata": "01-01-2025",
            "value_depreciated_import": "200.00",
            "value_salvage": "0.00",
        },
        {
            "name": "Computer 2",
            "value_original": "25000.00",
            "date_acquisition": "03-15-2025",
            "depreciation_method": "Declining",
            "depreciation_duration": "5",
            "depreciation_period": "Years",
            "depreciation_factor": "2",
            "depreciation_prorata": "Based on days per period",
            "date_prorata": "03-15-2025",
            "value_depreciated_import": "0.00",
            "value_salvage": "2000.00",
        },
        {
            "name": "Machine A",
            "value_original": "15000.00",
            "date_acquisition": "09-01-2024",
            "depreciation_method": "Straight Line",
            "depreciation_duration": "10",
            "depreciation_period": "Years",
            "depreciation_prorata": "Constant Periods",
            "date_prorata": "09-01-2024",
            "value_depreciated_import": "1500.00",
            "value_salvage": "500.00",
        },
        {
            "name": "Machine B",
            "value_original": "100000.00",
            "date_acquisition": "06-20-2025",
            "depreciation_method": "Straight Line",
            "depreciation_duration": "60",
            "depreciation_period": "Months",
            "depreciation_prorata": "No Prorata",
            "date_prorata": "06-20-2025",
            "value_depreciated_import": "10000.00",
            "value_salvage": "10000.00",
        },
    )

    def _get_technical_headers(self):
        return list(self.COLUMN_ORDER)

    def _get_localized_example_data(self, current_company_id, env):
        current_company = env["res.company"].browse(current_company_id)

        def account_name(account_types):
            for account_type in account_types:
                if (
                    account := env["account.account"]  # noqa: E8507  a short preference list, the first type with an account wins
                    .with_company(current_company)
                    .search(
                        [
                            *env["account.account"]._check_company_domain(
                                current_company
                            ),
                            ("account_type", "=", account_type),
                        ],
                        limit=1,
                    )
                ):
                    return (
                        account.display_name
                        if account.display_name.startswith(account.code)
                        else f"{account.code} {account.display_name}"
                    )
            return ""

        fixed_asset_account = account_name(["asset_fixed", "asset_non_current"])
        resolved = {
            "company_id": current_company.name,
            "account_asset_id": fixed_asset_account,
            "account_depreciation_id": fixed_asset_account,
            "account_depreciation_expense_id": account_name(
                ["expense_depreciation", "expense"]
            ),
            "depreciation_journal_id": env["account.journal"]
            .with_company(current_company)
            .search(
                [
                    *env["account.journal"]._check_company_domain(current_company),
                    ("type", "=", "general"),
                ],
                limit=1,
            )
            .name
            or "",
        }
        return [
            [example.get(fname, resolved.get(fname, "")) for fname in self.COLUMN_ORDER]
            for example in self.EXAMPLES
        ]

    def _get_instructions_data(self):
        described = {
            "name": (
                _("Asset Name"),
                True,
                _("Mandatory column. This is the name of the asset."),
            ),
            "value_original": (
                _("Original Value"),
                True,
                _("The amount will be considered in company currency."),
            ),
            "date_acquisition": (
                _("Acquisition Date"),
                True,
                _("e.g. 01-27-2025 (format: MM-DD-YYYY)"),
            ),
            "asset_group_id": (
                _("Asset Group"),
                False,
                _(
                    "Optional. The name or external ID of the asset group. Must exist in Odoo (e.g., Office Equipment, Vehicles, Machinery)."
                ),
            ),
            "depreciation_method": (
                _("Method"),
                True,
                _(
                    "e.g. Straight Line, Declining Balance. Determines how depreciation is calculated."
                ),
            ),
            "depreciation_duration": (
                _("Duration"),
                True,
                _(
                    "e.g. 3 for 3 years, or 12 for 12 months. It must be an integer representing the total number of periods."
                ),
            ),
            "depreciation_period": (
                _("Months/Years"),
                True,
                _(
                    'Either "Months" or "Years" (case-insensitive). Specifies the unit of duration.'
                ),
            ),
            "depreciation_factor": (
                _("Declining Factor"),
                False,
                _(
                    "Only applicable for Declining Balance method (e.g., 2 for double declining). Ignored for Straight Line."
                ),
            ),
            "depreciation_prorata": (
                _("Computation"),
                True,
                _(
                    "e.g. No Prorata, Constant Periods, Based on days per period. This determines how the first depreciation entry is calculated."
                ),
            ),
            "date_prorata": (
                _("Prorata Date"),
                True,
                _(
                    "Start date of the depreciation period. Should be in MM-DD-YYYY format. If left blank, it defaults to the acquisition date."
                ),
            ),
            "value_depreciated_import": (
                _("Depreciated Amount"),
                False,
                _(
                    "The total amount of depreciation already recorded for the asset before import. This amount will be considered in company currency."
                ),
            ),
            "value_salvage": (
                _("Not Depreciable Value"),
                False,
                _(
                    "The estimated residual value of the asset at the end of its useful life. This amount will not be depreciated. Considered in company currency."
                ),
            ),
            "company_id": (
                _("Company"),
                True,
                _(
                    "Must match the selected company during import. Use the company's display name."
                ),
            ),
            "account_asset_id": (
                _("Fixed Asset Account"),
                True,
                _(
                    'The balance sheet account for the asset itself (e.g., "151000 Fixed Asset"). Must exist in Odoo and be of "Fixed Asset" or "Non-current Assets" type.'
                ),
            ),
            "account_depreciation_id": (
                _("Depreciation Account"),
                True,
                _(
                    'The accumulated depreciation account (contra-asset account). Must exist in Odoo and be of "Fixed Asset" or "Non-current Assets" type.'
                ),
            ),
            "account_depreciation_expense_id": (
                _("Expense Account"),
                True,
                _(
                    'The expense account for posting periodic depreciation entries (e.g., "630000 Depreciation Expenses"). Must exist in Odoo and be of "Depreciation" or "Expense" type.'
                ),
            ),
            "depreciation_journal_id": (
                _("Journal"),
                True,
                _(
                    "The code or name of the associated journal in Odoo for depreciation entries (e.g., MISC - Miscellaneous Operations, INV - Customer Invoices, BILL - Vendor Bills)."
                ),
            ),
        }
        return [(fname, *described[fname]) for fname in self.COLUMN_ORDER]

    def _write_asset_sheet(self, workbook, headers, all_example_rows):
        worksheet_assets = workbook.add_worksheet("Assets")
        header_format = workbook.add_format({"bold": True})

        for col, header in enumerate(headers):
            worksheet_assets.write(0, col, header, header_format)

        for row_idx, example_row in enumerate(all_example_rows, start=1):
            for col, example_value in enumerate(example_row):
                worksheet_assets.write(row_idx, col, example_value)

        worksheet_assets.autofit()

    def _write_instructions_sheet(self, workbook, instructions_data):
        worksheet_instructions = workbook.add_worksheet("Instructions")

        instruction_headers = [
            "Column Name",
            "Column Functional Name",
            "Comments / Notes",
        ]
        instruction_header_format = workbook.add_format({"bold": True})

        for col_idx, header_text in enumerate(instruction_headers):
            worksheet_instructions.write(
                0, col_idx, header_text, instruction_header_format
            )

        for row_idx, (field, label, mandatory, help_text) in enumerate(
            instructions_data
        ):
            display_label = f"{label}*" if mandatory else label
            worksheet_instructions.write(row_idx + 1, 0, field)
            worksheet_instructions.write(row_idx + 1, 1, display_label)
            worksheet_instructions.write(row_idx + 1, 2, help_text)

        worksheet_instructions.autofit()

    def _generate_asset_import_template(self, company_id):
        technical_headers = self._get_technical_headers()
        all_example_rows = self._get_localized_example_data(company_id, request.env)
        instructions_data = self._get_instructions_data()

        output = io.BytesIO()
        with xlsxwriter.Workbook(output, {"in_memory": True}) as workbook:
            self._write_asset_sheet(workbook, technical_headers, all_example_rows)
            self._write_instructions_sheet(workbook, instructions_data)

        return output.getvalue()
