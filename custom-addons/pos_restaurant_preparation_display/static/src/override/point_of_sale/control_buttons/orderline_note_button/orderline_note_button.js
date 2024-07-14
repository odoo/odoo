/** @odoo-module **/
import { OrderlineNoteButton } from "@pos_restaurant/app/control_buttons/orderline_note_button/orderline_note_button";
import { patch } from "@web/core/utils/patch";

patch(OrderlineNoteButton.prototype, {
    // Override
    async click() {
        const { confirmed, inputNote, oldNote } = await super.click();
        const line = this.selectedOrderline;
        const productId = line.product.id;
        const order = line.order;

        if (confirmed) {
            if (!order.noteHistory) {
                order.noteHistory = {};
            }

            if (!order.noteHistory[productId]) {
                order.noteHistory[productId] = [];
            }

            let added = false;
            for (const note of order.noteHistory[productId]) {
                if (note.lineId === line.id) {
                    note.new = inputNote;
                    added = true;
                }
            }

            if (!added) {
                order.noteHistory[productId].push({
                    old: oldNote,
                    new: inputNote,
                    lineId: line.id,
                });
            }
        }
    },
});
