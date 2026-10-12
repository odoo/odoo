import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";
import { parseFloat } from "@web/views/fields/parsers";

patch(ControlButtons.prototype, {
    get lastDiscountTypeUsedKey() {
        return `pos_discount_last_type_used_${odoo.pos_config_id}`;
    },
    get lastDiscountTypeUsed() {
        return localStorage.getItem(this.lastDiscountTypeUsedKey) || "percent";
    },
    set lastDiscountTypeUsed(type) {
        localStorage.setItem(this.lastDiscountTypeUsedKey, type);
    },
    async clickDiscount() {
        const discountPc = this.pos.config.discount_pc || 0;
        const startingValue = formatFloat(discountPc, { trailingZeros: false });
        this.dialog.add(NumberPopup, {
            title: _t("Discount"),
            startingValue,
            startingType: this.lastDiscountTypeUsed,
            types: [
                { name: "fixed", symbol: this.pos.currency.symbol },
                { name: "percent", symbol: "%" },
            ],
            getPayload: (num, type) => {
                let value = this.pos.parseValidFloat(num.toString());
                if (type === "percent") {
                    value = Math.max(0, Math.min(100, value));
                }
                this.applyDiscount(value, type);
                this.lastDiscountTypeUsed = type;
            },
            formatDisplayedValue: (value, type) => {
                if (type === "fixed") {
                    return this.pos.formatCurrency(parseFloat(value));
                }
                if (type === "percent") {
                    return `${value} %`;
                }
                return value;
            },
        });
    },
    // FIXME business method in a compoenent, maybe to move in pos_store
    async applyDiscount(percent, type) {
        return this.pos.applyDiscount(percent, type);
    },
});
