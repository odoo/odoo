/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class PromoCodeButton extends Component {
    static template = "pos_loyalty.PromoCodeButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    async click() {
        let { confirmed, payload: code } = await this.popup.add(TextInputPopup, {
            title: _t("Enter Code"),
            startingValue: "",
            placeholder: _t("Gift card or Discount code"),
        });
        if (confirmed) {
            code = code.trim();
            if (code !== "") {
                this.pos.get_order().activateCode(code);
            }
        }
    }
}

ProductScreen.addControlButton({
    component: PromoCodeButton,
    condition: function () {
        return this.pos.programs.some((p) =>
            ["coupons", "promotion", "gift_card", "promo_code", "next_order_coupons"].includes(p.program_type)
        );
    },
});
