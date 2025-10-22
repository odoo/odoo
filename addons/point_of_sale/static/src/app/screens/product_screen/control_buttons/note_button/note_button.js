import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

export class NoteButton extends Component {
    static template = "point_of_sale.NoteButton";
    static props = {
        icon: { type: String, optional: true },
        label: { type: String, optional: false },
        type: { type: String, optional: false },
        class: { type: String, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    onClick() {
        return this.pos.getOrder()?.getSelectedOrderline()
            ? this.addLineNote()
            : this.addOrderNote();
    }

    async addLineNote() {
        const selectedOrderline = this.pos.getOrder().getSelectedOrderline();
        const selectedNote = this.currentNote || "";
        const oldNote = selectedOrderline.getNote();
        const payload = await this.openTextInput(selectedNote);
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
            const newLine = await this.pos.addLineToCurrentOrder({
                product_tmpl_id: selectedOrderline.product_id.product_tmpl_id,
                qty: quantity_with_note,
                note: payload,
            });
            if (newLine) {
                newLine.combo_line_ids.forEach((child) => {
                    child.qty = quantity_with_note;
                });
                selectedOrderline.qty = saved_quantity;
                selectedOrderline.combo_line_ids.forEach((child) => {
                    child.qty = saved_quantity;
                });
            }
        } else {
            this.setNote(payload);
        }
        return { confirmed: typeof payload === "string", inputNote: payload, oldNote };
    }

    async addOrderNote() {
        const selectedNote = this.currentNote || "";
        const payload = await this.openTextInput(selectedNote);
        this.setNote(payload);
        return { confirmed: typeof payload === "string", inputNote: payload };
    }

    async openTextInput(selectedNote) {
        let buttons = [];
        if (
            this.props.type === "internal" ||
            this.pos.getOrder()?.getSelectedOrderline() === undefined
        ) {
            buttons = this.pos.models["pos.note"].getAll().map((note) => ({
                label: note.name,
                isSelected: selectedNote.split("\n").includes(note.name), // Check if the note is already selected
            }));
        }
        return await makeAwaitable(this.dialog, TextInputPopup, {
            title: _t("Add %s", this.props.label),
            buttons,
            rows: 4,
            startingValue: selectedNote,
        });
    }

    get orderNote() {
        const order = this.pos.getOrder();
        return this.props.type === "internal"
            ? order.internal_note || ""
            : order.general_customer_note || "";
    }

    get orderlineNote() {
        const orderline = this.pos.getOrder().getSelectedOrderline();
        return this.props.type === "internal" ? orderline.getNote() : orderline.getCustomerNote();
    }

    get currentNote() {
        return this.pos.getOrder().getSelectedOrderline() ? this.orderlineNote : this.orderNote;
    }

    setOrderNote(value) {
        const order = this.pos.getOrder();
        return this.props.type === "internal"
            ? order.setInternalNote(value)
            : order.setGeneralCustomerNote(value);
    }

    setOrderlineNote(value) {
        const orderline = this.pos.getOrder().getSelectedOrderline();
        return this.props.type === "internal"
            ? orderline.setNote(value)
            : orderline.setCustomerNote(value);
    }

    setNote(note) {
        return this.pos.getOrder().getSelectedOrderline()
            ? this.setOrderlineNote(note)
            : this.setOrderNote(note);
    }
}
