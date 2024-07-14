# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import csv
import io

from odoo import api, models, fields


class Generate1099Wizard(models.TransientModel):
    _name = "l10n_us_1099.wizard"
    _description = "Exports 1099 data to a CSV file."

    def _default_start_date(self):
        """ Return the first day of last year. """
        today = fields.Date.today()
        return today.replace(today.year - 1, 1, 1)

    def _default_end_date(self):
        """ Return the last day of last year. """
        today = fields.Date.today()
        return today.replace(today.year - 1, 12, 31)

    start_date = fields.Date(
        "Start Date",
        default=_default_start_date,
        required=True,
        help="The wizard will auto-populate journal items on and after this date."
    )
    end_date = fields.Date(
        "End Date", default=_default_end_date,
        required=True,
        help="The wizard will auto-populate journal items before and on this date."
    )
    lines_to_export = fields.Many2many(
        "account.move.line",
        string="Journal Items To Include",
        compute="_compute_lines_to_export",
        readonly=False,
        store=True,
        help="These journal items will be included in the generated CSV file."
    )
    generated_csv_file = fields.Binary(
        "Generated file",
        help="Technical field used to temporarily hold the generated CSV file before it's downloaded."
    )

    @api.depends("start_date", "end_date")
    def _compute_lines_to_export(self):
        """ This adds lines that moved money out of an asset (e.g. a bank account) to a vendor that requires a 1099.
        The IRS wants only money payments, so we cannot use journal items on other accounts (e.g. Rent or Expense)
        since they can be paid in different ways (e.g. a credit somewhere else). It also should show refunds for vendor bills,
        since they are allowed to use to offset the reported amount."""
        for wizard in self:
            wizard.lines_to_export = self.env["account.move.line"]
            lines = self.env["account.move.line"].search([
                ("company_id", "in", self.env.companies.ids),
                ("parent_state", "=", "posted"),
                ("currency_id", "=", self.env.ref("base.USD").id),
                ("partner_id.box_1099_id", "!=", False),
                ("date", ">=", wizard.start_date),
                ("date", "<=", wizard.end_date),
                # everything in accounts under Balance Sheet > Assets that's liquid
                ("account_id.internal_group", "=", "asset"),
                ("account_id.account_type", "in", ("asset_cash", "liability_credit_card")),
            ], order="partner_id,date")

            # only allow positive lines if they're related to a vendor bill refund
            for line in lines:
                if line.balance > 0:
                    reconciled_lines = line.move_id.line_ids._reconciled_lines()
                    types = self.env['account.move.line'].browse(reconciled_lines).mapped('move_id').mapped('move_type')
                    if "in_refund" in types:
                        wizard.lines_to_export |= line
                else:
                    wizard.lines_to_export |= line

    def _generate_row(self, company, vendor, total, boxes_1099):
        """ Generates a single row in the output CSV. Will attribute the total to the box specified on the partner. """
        row = [
            company.display_name,
            company.street,
            company.street2,
            company.city,
            company.state_id.name,
            company.zip,
            company.country_id.name,
            company.phone,
            company.vat,
            vendor.display_name,
            vendor.street,
            vendor.street2,
            vendor.city,
            vendor.state_id.name,
            vendor.zip,
            vendor.country_id.name,
            vendor.email,
            vendor.vat,
        ]
        row = [val or "" for val in row]  # replace False m2o's

        for box_1099 in boxes_1099:
            if box_1099 == vendor.box_1099_id:
                row.append(-total)  # payments to vendors will be negative, so flip the sign
            else:
                row.append(0)

        return row

    def action_generate(self):
        """ Called from UI. Generates the CSV file in memory and writes it to the generated_csv_file
        field. Then returns an action for the client to download it. """
        self.ensure_one()
        header = [
            "Payer Name",
            "Payer Address Line 1",
            "Payer Address Line 2",
            "Payer City",
            "Payer State",
            "Payer Zip",
            "Payer Country",
            "Payer Phone Number",
            "Payer TIN",
            "Payee Name",
            "Payee Address Line 1",
            "Payee Address Line 2",
            "Payee City",
            "Payee State",
            "Payee Zip",
            "Payee Country",
            "Payee Email",
            "Payee TIN",
        ]
        boxes_1099 = self.env["l10n_us.1099_box"].search([])
        header += boxes_1099.mapped("name")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        curr_vendor = None
        curr_total = 0
        lines = self.lines_to_export.sorted(lambda l: l.partner_id.id)
        for line in lines:
            if curr_vendor != line.partner_id and curr_total != 0:
                curr_total = self.env.ref("base.USD").round(curr_total)
                new_row = self._generate_row(line.company_id, curr_vendor, curr_total, boxes_1099)
                writer.writerow(new_row)

                curr_vendor = line.partner_id
                curr_total = line.balance
            else:
                curr_vendor = line.partner_id
                curr_total += line.balance

        if curr_total != 0:
            curr_total = self.env.ref("base.USD").round(curr_total)
            writer.writerow(self._generate_row(lines[-1].company_id, curr_vendor, curr_total, boxes_1099))

        self.generated_csv_file = base64.b64encode(output.getvalue().encode())

        us_format = "%m_%d_%Y"
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=l10n_us_1099.wizard&download=true&field=generated_csv_file&filename=1099 report {} - {}.csv&id={}".format(
                self.start_date.strftime(us_format), self.end_date.strftime(us_format), self.id
            ),
        }
