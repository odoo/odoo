/** @odoo-module **/

import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";

export const PosEventProductScreen = (ProductScreen) => class extends ProductScreen {
    async _onClickPay() {
        const order = this.env.pos.get_order();
        const hasEventLines = order.get_orderlines().some(line => line.eventId);
        if (hasEventLines && !order.get_partner()) {
            const {confirmed} = await this.showPopup("ConfirmPopup", {
                title: this.env._t("Customer needed"),
                body: this.env._t("Buying event ticket requires a customer to be selected"),
            });
            if (confirmed) {
                const { confirmed, payload: newPartner } = await this.showTempScreen(
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
            return super._onClickPay(...arguments);
        }
    }
};

Registries.Component.extend(ProductScreen, PosEventProductScreen);
