/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener, useService } from "@web/core/utils/hooks";
import { TextAreaPopup } from "@point_of_sale/js/Popups/TextAreaPopup";

export class OrderlineNoteButton extends LegacyComponent {
    static template = "OrderlineNoteButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
        useListener("click", this.onClick);
    }
    get selectedOrderline() {
        return this.env.pos.get_order().get_selected_orderline();
    }
    async onClick() {
        if (!this.selectedOrderline) {
            return;
        }

        const { confirmed, payload: inputNote } = await this.popup.add(TextAreaPopup, {
            startingValue: this.selectedOrderline.get_note(),
            title: this.env._t("Add Internal Note"),
        });

        if (confirmed) {
            this.selectedOrderline.set_note(inputNote);
        }
    }
}

ProductScreen.addControlButton({
    component: OrderlineNoteButton,
    condition: function () {
        return this.env.pos.config.iface_orderline_notes;
    },
});
