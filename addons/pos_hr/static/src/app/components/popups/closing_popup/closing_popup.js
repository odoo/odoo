import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    hasUserAuthority() {
        if (!this.pos.config.module_pos_hr) {
            return super.hasUserAuthority();
        }
        const cashier = this.pos.cashier;
        return (
            (cashier._role == "manager" && cashier._user_role == "admin") ||
            this.allowedDifference()
        );
    },
    get cashTransactionSummary() {
        const transactions = super.cashTransactionSummary;
        const cashBreakdown = this.props.default_cash_details.cash_breakdown;
        if (this.pos.config.module_pos_hr && cashBreakdown.amount_per_employee.length) {
            transactions.list.splice(-1, 1, ...cashBreakdown.amount_per_employee);
        }
        return transactions;
    },
});
