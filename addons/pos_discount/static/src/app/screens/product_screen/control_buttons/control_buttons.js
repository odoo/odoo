import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        this.dialog.add(NumberPopup, {
<<<<<<< b7c9c140eb04222626fa92e926e86b2fea213476
            title: _t("Discount"),
            startingValue: String(this.pos.config.discount_pc || 0),
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
                    return this.env.utils.formatCurrency(parseFloat(value));
                }
                if (type === "percent") {
                    return `${value} %`;
                }
                return value;
||||||| 88df50bc96448dfaff28bd37e970ffd18bf8d554
            title: _t("Discount Percentage"),
            startingValue: this.pos.config.discount_pc,
            getPayload: (num) => {
                const percent = Math.max(
                    0,
                    Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                );
                this.applyDiscount(percent);
=======
            title: _t("Discount Percentage"),
            startingValue: this.env.utils.formatCurrency(this.pos.config.discount_pc, false),
            getPayload: (num) => {
                const percent = Math.max(
                    0,
                    Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                );
                this.applyDiscount(percent);
>>>>>>> d2c66a5e5be9300ff6de02dcaa2bb7a85c8b28dc
            },
        });
    },
    // FIXME business method in a compoenent, maybe to move in pos_store
    async applyDiscount(percent, type) {
        return this.pos.applyDiscount(percent, type);
    },
});
