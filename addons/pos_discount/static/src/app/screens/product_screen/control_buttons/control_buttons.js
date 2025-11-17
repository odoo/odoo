import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        this.dialog.add(NumberPopup, {
            title: _t("Discount Percentage"),
            startingValue: this.pos.config.discount_pc,
            startingType: "percent",
            types: [
                { name: "fixed", symbol: this.pos.currency.symbol },
                { name: "percent", symbol: "%" },
            ],
            getPayload: (num, type) => {
                let value = num;
                if (type === "percent") {
                    value = Math.max(
                        0,
                        Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                    );
                }
                this.applyDiscount(value, type);
            },
            formatDisplayedValue: (value, type) => {
                if (type === "fixed") {
                    return this.env.utils.formatCurrency(value);
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
