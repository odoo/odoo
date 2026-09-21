/** @odoo-module native */
import { AccountReportChatter } from "@account/components/mail/chatter";
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { patch } from "@web/core/utils/patch";

patch(AccountReport, {
    components: { ...AccountReport.components, AccountReportChatter },
});

patch(AccountReport.prototype, {
    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.controller.closeChatter();
        }
    },

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (
            this.ui.isSmall &&
            this.controller.chatterState.id &&
            !ev.target.closest(".o_account_report_mobile_chatter")
        ) {
            this.controller.closeChatter();
        }
    },
});
