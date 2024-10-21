import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

export class OrderlineNoteButton extends Component {
    static template = "point_of_sale.OrderlineNoteButton";
    static props = {
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
        getter: { type: Function, optional: true },
        setter: { type: Function, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
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
        const payload = await this.openTextInput(selectedNote, false);
        this.setChanges(selectedOrderline, payload);
        return { confirmed: typeof payload === "string", inputNote: payload };
    }

    // Update line changes and set them
    async setChanges(selectedOrderline, payload) {
        var quantity_with_note = 0;
        const changes = this.pos.getOrderChanges();
        for (const key in changes.orderlines) {
            if (changes.orderlines[key].uuid == selectedOrderline.uuid) {
                quantity_with_note = changes.orderlines[key].quantity;
                break;
            }
        }
        const saved_quantity = selectedOrderline.qty - quantity_with_note;
        if (saved_quantity > 0 && quantity_with_note > 0) {
            await this.pos.addLineToCurrentOrder({
                product_id: selectedOrderline.product_id,
                product_tmpl_id: selectedOrderline.product_id.product_tmpl_id,
                qty: quantity_with_note,
                note: payload,
            });
            selectedOrderline.qty = saved_quantity;
        } else {
            this.props.setter(selectedOrderline, payload);
        }
        return { quantity_with_note, saved_quantity };
    }

    // Useful to handle name and color together for internal notes
    reframeNotes(payload) {
        const allnotes = [];
        for (const noteName of payload.split("\n")) {
            const defaultNote = this.pos.models["pos.note"].find((note) => note.name === noteName);
            if (defaultNote && noteName.trim()) {
                allnotes.push({ text: noteName, colorIndex: defaultNote.color });
            } else if (noteName.trim()) {
                const newColor = Math.floor(Math.random() * 11);
                allnotes.push({ text: noteName, colorIndex: newColor });
            }
        }
        return JSON.stringify(allnotes);
    }

    async openTextInput(selectedNote, displayNotes) {
        let buttons = [];
        if (displayNotes) {
            buttons = this.pos.models["pos.note"].getAll().map((note) => ({
                label: note.name,
                isSelected: selectedNote.includes(note.name), // Check if the note is already selected
                class: note.color ? `o_colorlist_item_color_${note.color}` : "",
            }));
        }
        return await makeAwaitable(this.dialog, TextInputPopup, {
            title: _t("Add %s", this.props.label),
            buttons,
            rows: 4,
            startingValue: selectedNote,
        });
    }
}

export class InternalNoteButton extends OrderlineNoteButton {
    static template = "point_of_sale.OrderlineNoteButton";
    static props = {
        ...OrderlineNoteButton.props,
    };
    async onClick() {
        const selectedOrderline = this.pos.get_order().get_selected_orderline();
        const selectedNote = JSON.parse(this.props.getter(selectedOrderline) || "[]");
        const payload = await this.openTextInput(selectedNote.map((n) => n.text).join("\n"), true);
        const coloredNotes = this.reframeNotes(payload);
        this.setChanges(selectedOrderline, coloredNotes);
        return {
            confirmed: typeof payload === "string",
            inputNote: coloredNotes,
            oldNote: JSON.stringify(selectedNote),
        };
    }
}
