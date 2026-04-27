import { _t } from "@web/core/l10n/translation";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { patch } from "@web/core/utils/patch";

patch(CashMovePopup.prototype, {
    setup() {
        super.setup();
        this.state.reason_type = "";
    },
    onClickButton(type) {
        super.onClickButton(type);
        this.state.reason_type = "";
    },
    _prepare_try_cash_in_out_payload(type, amount, reason, partnerId, extras) {
        // used to retrieve the reason type in backend at the time of session closing
        // If we change the format of the reason here, we also need to change it in `get_cash_statement_cases` of pos.session
        const result = super._prepare_try_cash_in_out_payload(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            result[3] = `${this.state.reason_type}-${reason}`;
        }
        return result;
    },
    isValidCashMove() {
        const validCashMove = super.isValidCashMove();
        if (this.pos.isCountryGermanyAndFiskaly()) {
            return validCashMove && this.state.reason_type.trim() !== "";
        }
        return validCashMove;
    },
    get categoryReasons() {
        const commonOptions = [
            { value: "", label: _t("Select a category") },
            { value: "geldtransit", label: _t("Cash Transfer") },
        ];
        const outOptions = [
            { value: "privatentnahme", label: _t("Private Withdrawal") },
            { value: "auszahlung", label: _t("Payout") },
            { value: "lohnzahlung", label: _t("Wage Payment") },
        ];
        const inOptions = [
            { value: "privateinlage", label: _t("Private Deposit") },
            { value: "einzahlung", label: _t("Deposit") },
            { value: "zuschussEcht", label: _t("Cash Supplement") },
        ];
        return this.state.type === "out"
            ? [...commonOptions, ...outOptions]
            : [...commonOptions, ...inOptions];
    },
});
