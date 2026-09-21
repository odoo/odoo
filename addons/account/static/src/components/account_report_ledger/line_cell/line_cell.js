/** @odoo-module native */
import { AccountReportLineCell } from "@account/components/account_report/line_cell/line_cell";
import { AccountReportCarryoverPopover } from "@account/components/account_report_ledger/line_cell/carryover_popover";
import { localization } from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";

patch(AccountReportLineCell.prototype, {
    carryoverPopover(ev) {
        if (this.popoverCloseFn) {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountReportCarryoverPopover,
            {
                carryoverData: JSON.parse(this.props.cell.info_popup_data),
                options: this.controller.options,
                context: this.controller.context,
            },
            {
                closeOnClickAway: true,
                position: localization.direction === "rtl" ? "bottom" : "right",
            },
        );
    },
});
