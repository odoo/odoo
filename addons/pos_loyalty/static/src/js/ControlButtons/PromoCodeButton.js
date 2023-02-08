/** @odoo-module **/

import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener, useService } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";

export class PromoCodeButton extends LegacyComponent {
    static template = "PromoCodeButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
        useListener("click", this.onClick);
    }

    async onClick() {
        let { confirmed, payload: code } = await this.popup.add(TextInputPopup, {
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
