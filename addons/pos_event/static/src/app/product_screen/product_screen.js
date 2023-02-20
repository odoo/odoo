/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";

patch(ProductScreen.prototype, "pos_event.ProductScreen", {
    async _onClickPay() {
        const order = this.env.pos.get_order();
        const _super = this._super;
        if (order.hasEventLines() && !order.get_partner()) {
            const {confirmed} = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Customer needed"),
                body: this.env._t("Buying event ticket requires a customer to be selected"),
            });
            if (confirmed) {
                const { confirmed, payload: newPartner } = await this.pos.showTempScreen(
                    "PartnerListScreen",
                    { partner: null }
                );
                if (confirmed) {
                    // todo refactor set_partner with updatePricelist in the whole pos
                    order.set_partner(newPartner);
                    order.updatePricelist(newPartner);
                }
            }
        } else {
            return _super(...arguments);
        }
    }
});
