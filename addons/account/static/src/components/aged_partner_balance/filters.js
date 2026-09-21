/** @odoo-module native */
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportFilters } from "@report_formula/components/account_report/filters/filters";
import { WarningDialog } from "@web/components/errors";
import { _t } from "@web/core/translation";

export class AgedPartnerBalanceFilters extends AccountReportFilters {
    static template = "account.AgedPartnerBalanceFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Aging Interval
    //------------------------------------------------------------------------------------------------------------------
    async setAgingInterval(ev) {
        const agingInterval = parseInt(ev.target.value);
        if (agingInterval < 1) {
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Intervals cannot be smaller than 1"),
            });
            return;
        }

        await this.filterClicked({
            optionKey: "aging_interval",
            optionValue: agingInterval,
            reload: true,
        });
    }

    get filterExtraOptionsData() {
        return {
            ...super.filterExtraOptionsData,
            show_currency: {
                name: _t("Show Currency"),
                show: this.controller.cachedFilterOptions.multi_currency,
            },
            show_account: {
                name: _t("Show Account"),
            },
        };
    }
}

AccountReport.registerCustomComponent(AgedPartnerBalanceFilters);
