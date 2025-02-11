/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { TextAreaPopup } from "@point_of_sale/app/utils/input_popups/textarea_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderlineCustomerNoteButton extends Component {
    static template = "point_of_sale.OrderlineCustomerNoteButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    async onClick() {
        const selectedOrderline = this.pos.get_order().get_selected_orderline();
        // FIXME POSREF can this happen? Shouldn't the orderline just be a prop?
        if (!selectedOrderline) {
            return;
        }
        const { confirmed, payload: inputNote } = await this.popup.add(TextAreaPopup, {
            startingValue: selectedOrderline.get_customer_note(),
            title: _t("Add Customer Note"),
        });

        if (confirmed) {
            selectedOrderline.set_customer_note(inputNote);
        }
    }
}

ProductScreen.addControlButton({
    component: OrderlineCustomerNoteButton,
});
