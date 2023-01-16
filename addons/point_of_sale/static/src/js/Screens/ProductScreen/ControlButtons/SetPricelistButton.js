/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import { SelectionPopup } from "@point_of_sale/js/Popups/SelectionPopup";

export class SetPricelistButton extends PosComponent {
    static template = "SetPricelistButton";

    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    get currentPricelistName() {
        const order = this.currentOrder;
        return order && order.pricelist ? order.pricelist.display_name : this.env._t("Pricelist");
    }
    async onClick() {
        // Create the list to be passed to the SelectionPopup.
        // Pricelist object is passed as item in the list because it
        // is the object that will be returned when the popup is confirmed.
        const selectionList = this.env.pos.pricelists.map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist && pricelist.id === this.currentOrder.pricelist.id,
            item: pricelist,
        }));

        if (!this.env.pos.default_pricelist) {
            selectionList.push({
                id: null,
                label: this.env._t("Default Price"),
                isSelected: !this.currentOrder.pricelist,
                item: null,
            });
        }

        const { confirmed, payload: selectedPricelist } = await this.showPopup(SelectionPopup, {
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
        return this.env.pos.config.use_pricelist && this.env.pos.pricelists.length > 0;
    },
});
