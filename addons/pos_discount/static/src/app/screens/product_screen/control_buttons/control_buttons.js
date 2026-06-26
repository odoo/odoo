import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";
import { parseFloat } from "@web/views/fields/parsers";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        const discountPc = this.pos.config.discount_pc || 0;
        const startingValue = formatFloat(discountPc, { trailingZeros: false });
        this.dialog.add(NumberPopup, {
            title: _t("Discount"),
            startingValue,
            startingType: "percent",
            types: [
                { name: "fixed", symbol: this.pos.currency.symbol },
                { name: "percent", symbol: "%" },
            ],
            getPayload: (num, type) => {
                let value = this.env.utils.parseValidFloat(num.toString());
                if (type === "percent") {
                    value = Math.max(0, Math.min(100, value));
                }
                this.applyDiscount(value, type);
            },
            formatDisplayedValue: (value, type) => {
                if (type === "fixed") {
                    return this.env.utils.formatCurrency(parseFloat(value));
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
