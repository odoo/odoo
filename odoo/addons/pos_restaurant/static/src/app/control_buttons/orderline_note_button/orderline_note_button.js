/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { TextAreaPopup } from "@point_of_sale/app/utils/input_popups/textarea_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderlineNoteButton extends Component {
    static template = "pos_restaurant.OrderlineNoteButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get selectedOrderline() {
        return this.pos.get_order().get_selected_orderline();
    }
    async click() {
        if (!this.selectedOrderline) {
            return;
        }

        const oldNote = this.selectedOrderline.getNote();
        const { confirmed, payload: inputNote } = await this.popup.add(TextAreaPopup, {
            startingValue: this.selectedOrderline.getNote(),
            title: _t("Add internal Note"),
        });

        if (confirmed) {
            this.selectedOrderline.setNote(inputNote);
        }

        return { confirmed, inputNote, oldNote };
    }
}

ProductScreen.addControlButton({
    component: OrderlineNoteButton,
    condition: function () {
        return this.pos.config.iface_orderline_notes;
    },
});
