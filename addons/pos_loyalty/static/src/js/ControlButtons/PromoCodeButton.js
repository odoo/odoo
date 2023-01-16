/** @odoo-module **/

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";

export class PromoCodeButton extends PosComponent {
    static template = "PromoCodeButton";

    setup() {
        super.setup();
        useListener("click", this.onClick);
    }

    async onClick() {
        let { confirmed, payload: code } = await this.showPopup(TextInputPopup, {
            title: this.env._t("Enter Code"),
            startingValue: "",
            placeholder: this.env._t("Gift card or Discount code"),
        });
        if (confirmed) {
            code = code.trim();
            if (code !== "") {
                this.env.pos.get_order().activateCode(code);
            }
        }
    }
}

ProductScreen.addControlButton({
    component: PromoCodeButton,
    condition: function () {
        return this.env.pos.programs.some((p) =>
            ["coupons", "promotion", "gift_card"].includes(p.program_type)
        );
    },
});
