/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { TextAreaPopup } from "@point_of_sale/js/Popups/TextAreaPopup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class OrderlineNoteButton extends Component {
    static template = "OrderlineNoteButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get selectedOrderline() {
        return this.pos.globalState.get_order().get_selected_orderline();
    }
    async click() {
        if (!this.selectedOrderline) {
            return;
        }

        const { confirmed, payload: inputNote } = await this.popup.add(TextAreaPopup, {
            startingValue: this.selectedOrderline.getNote(),
            title: this.env._t("Add internal Note"),
        });

        if (confirmed) {
            this.selectedOrderline.setNote(inputNote);
        }
    }
}

ProductScreen.addControlButton({
    component: OrderlineNoteButton,
    condition: function () {
        return this.pos.globalState.config.iface_orderline_notes;
    },
});
