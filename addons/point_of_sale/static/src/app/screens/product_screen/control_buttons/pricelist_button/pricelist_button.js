/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { SelectionPopup } from "@point_of_sale/js/Popups/SelectionPopup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class SetPricelistButton extends Component {
    static template = "SetPricelistButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get currentOrder() {
        return this.pos.globalState.get_order();
    }
    get currentPricelistName() {
        const order = this.currentOrder;
        return order && order.pricelist ? order.pricelist.display_name : this.env._t("Pricelist");
    }
    async click() {
        // Create the list to be passed to the SelectionPopup.
        // Pricelist object is passed as item in the list because it
        // is the object that will be returned when the popup is confirmed.
        const selectionList = this.pos.globalState.pricelists.map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist && pricelist.id === this.currentOrder.pricelist.id,
            item: pricelist,
        }));

        if (!this.pos.globalState.default_pricelist) {
            selectionList.push({
                id: null,
                label: this.env._t("Default Price"),
                isSelected: !this.currentOrder.pricelist,
                item: null,
            });
        }

        const { confirmed, payload: selectedPricelist } = await this.popup.add(SelectionPopup, {
            title: this.env._t("Select the pricelist"),
            list: selectionList,
        });

        if (confirmed) {
            this.currentOrder.set_pricelist(selectedPricelist);
        }
    }
}

ProductScreen.addControlButton({
    component: SetPricelistButton,
    condition: function () {
        const { config, pricelists } = this.pos.globalState;
        return config.use_pricelist && pricelists.length > 0;
    },
});
