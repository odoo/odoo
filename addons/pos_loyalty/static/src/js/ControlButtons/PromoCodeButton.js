/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class PromoCodeButton extends Component {
    static template = "PromoCodeButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    async click() {
        let { confirmed, payload: code } = await this.popup.add(TextInputPopup, {
            title: this.env._t("Enter Code"),
            startingValue: "",
            placeholder: this.env._t("Gift card or Discount code"),
        });
        if (confirmed) {
            code = code.trim();
            if (code !== "") {
                this.pos.globalState.get_order().activateCode(code);
            }
        }
    }
}

ProductScreen.addControlButton({
    component: PromoCodeButton,
    condition: function () {
        return this.pos.globalState.programs.some((p) =>
            ["coupons", "promotion", "gift_card", "promo_code"].includes(p.program_type)
        );
    },
});
