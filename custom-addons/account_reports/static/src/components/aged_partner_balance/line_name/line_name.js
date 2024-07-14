/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLineName } from "@account_reports/components/account_report/line_name/line_name";
import { ExpectedDateDialog } from "@account_reports/components/aged_partner_balance/dialog/expected_date_dialog";

import { formatDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class AgedPartnerBalanceLineName extends AccountReportLineName {
    static template = "account_reports.AgedPartnerBalanceLineName";

    setup() {
        this.dialog = useService("dialog");

        super.setup();
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Dialog
    // -----------------------------------------------------------------------------------------------------------------
    async openExpectedDateDialog() {
        const date = DateTime.fromISO(this.props.line.columns.find(column => column.expression_label === 'expected_date')?.no_format);
        this.dialog.add(ExpectedDateDialog, {
            title: _t("Change expected date"),
            size: "md",
            default_date: date.invalid ? null : date,
            save: this.saveExpectedDate.bind(this),
        });
    }

    async saveExpectedDate(ev, date) {
        if (date) {
            await this.controller.reportAction(
                ev,
                "change_expected_date",
                {
                    line_id: this.props.line.id,
                    expected_pay_date: date.toFormat("yyyy-MM-dd"),
                }
            );

            const expectedDateColumnIndex = this.controller.options.columns.findIndex(column => column.expression_label === 'expected_date');
            this.props.line.columns[expectedDateColumnIndex].no_format = date.toFormat("yyyy-MM-dd");
            this.props.line.columns[expectedDateColumnIndex].name = formatDate(date);
        }
    }
}

AccountReport.registerCustomComponent(AgedPartnerBalanceLineName);
