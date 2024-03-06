/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

export class OrderlineNoteButton extends Component {
    static template = "point_of_sale.OrderlineNoteButton";
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
        const oldNote = selectedOrderline.getNote();
        const payload = await makeAwaitable(this.dialog, TextInputPopup, {
            startingValue: this.props.getter(selectedOrderline),
            title: _t("Add %s", this.props.label),
        });

        if (typeof payload === "string") {
            this.props.setter(selectedOrderline, payload);
        }

        return { confirmed: typeof payload === "string", inputNote: payload, oldNote };
    }
}
