/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { useService } from "@web/core/utils/hooks";

export class OrderlineNoteButton extends Component {
    static template = "point_of_sale.OrderlineNoteButton";
    static props = {
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
        getter: { type: Function, optional: true },
        setter: { type: Function, optional: true },
    };
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
        const selectedNote = this.props.getter(selectedOrderline);
        const notes = this.pos.models["pos.note"].getAll();
        let buttons;
        if (this.props.label == _t("Internal Note")) {
            buttons = notes.map((note) => ({
                label: note.name,
                isSelected: selectedNote.split("\n").includes(note.name), // Check if the note is already selected
            }));
        } else {
            buttons = [];
        }
        this.dialog.add(TextInputPopup, {
            title: _t("Add %s", this.props.label),
            buttons,
            rows: 4,
            startingValue: this.props.getter(selectedOrderline),
            getPayload: (note) => {
                this.props.setter(selectedOrderline, note);
            },
        });
    }
}
