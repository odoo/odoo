/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLineName } from "@account_reports/components/account_report/line_name/line_name";

export class LUAppendixLineName extends AccountReportLineName {
    static template = "l10n_lu_reports.AppendixLineName";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    async recomputeAction(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.dialogService.add(ConfirmationDialog, {
            body: _t("You are about to delete all this year's appendix lines and calculate new ones. This action is irreversible."),
            confirmLabel: _t("Proceed"),
            confirm: async () => {
                await this.controller.reportAction(ev, 'action_open_appendix_view', {'recompute': true});
            },
            cancel: () => { },
        });
    }
}

AccountReport.registerCustomComponent(LUAppendixLineName);
