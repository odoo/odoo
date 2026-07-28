/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SetPricelistButton extends Component {
    static template = "point_of_sale.SetPricelistButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get currentPricelistName() {
        const order = this.currentOrder;
        return order && order.pricelist ? order.pricelist.display_name : _t("Pricelist");
    }
    /**
     * Create the list to be passed to the SelectionPopup on the `click` function.
     * Pricelist object is passed as item in the list because it
     * is the object that will be returned when the popup is confirmed.
     * @returns {Array}
     */
    getPricelistList() {
        const selectionList = this.pos.pricelists.map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist && pricelist.id === this.currentOrder.pricelist.id,
            item: pricelist,
        }));

        if (!this.pos.default_pricelist) {
            selectionList.push({
                id: null,
                label: _t("Default Price"),
                isSelected: !this.currentOrder.pricelist,
                item: null,
            });
        }
        return selectionList;
    }
    async click() {
        const selectionList = this.getPricelistList();

        const { confirmed, payload: selectedPricelist } = await this.popup.add(SelectionPopup, {
            title: _t("Select the pricelist"),
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
        const { config, pricelists } = this.pos;
        return config.use_pricelist && pricelists.length > 0;
    },
});
