/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { useService } from "@web/core/utils/hooks";

export class OrderlineCustomerNoteButton extends Component {
    static template = "point_of_sale.OrderlineCustomerNoteButton";
    static defaultProps = {
        icon: "fa fa-sticky-note",
        label: _t("Customer Note"),
        getter: (orderline) => orderline.get_customer_note(),
        setter: (orderline, note) => orderline.set_customer_note(note),
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }
    async onClick() {
        const selectedOrderline = this.pos.get_order().get_selected_orderline();
        this.dialog.add(TextInputPopup, {
            rows: 4,
            startingValue: this.props.getter(selectedOrderline),
            title: _t("Add %s", this.props.label),
            getPayload: (note) => {
                this.props.setter(selectedOrderline, note);
            },
        });
    }
}

ProductScreen.addControlButton({
    component: OrderlineCustomerNoteButton,
});
