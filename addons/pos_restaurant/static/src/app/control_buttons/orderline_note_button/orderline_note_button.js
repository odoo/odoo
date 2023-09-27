/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { OrderlineCustomerNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_note_button/customer_note_button";
import { Component, xml } from "@odoo/owl";

export class OrderlineNoteButton extends Component {
    static components = { OrderlineCustomerNoteButton };
    static template = xml`
        <OrderlineCustomerNoteButton
            icon="'fa fa-tag'"
            label="'Internal Note'"
            getter="(orderline) => orderline.getNote()"
            setter="(orderline, note) => orderline.setNote(note)" />
    `;
}
ProductScreen.addControlButton({
    component: OrderlineNoteButton,
    condition: function () {
        return this.pos.config.iface_orderline_notes;
    },
});
