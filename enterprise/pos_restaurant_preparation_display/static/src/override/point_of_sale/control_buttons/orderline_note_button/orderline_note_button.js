import { OrderlineNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_note_button/customer_note_button";
import { patch } from "@web/core/utils/patch";

patch(OrderlineNoteButton.prototype, {
    // Override
    async onClick() {
        const { confirmed, inputNote, oldNote } = await super.onClick();
        if (!this._isInternalNote()) {
            return { confirmed, inputNote, oldNote };
        }
        const selectedOrderline = this.pos.get_order().get_selected_orderline();
        const productId = selectedOrderline.product_id.id;
        const order = selectedOrderline.order_id;

        if (confirmed) {
            if (!order.uiState.noteHistory) {
                order.uiState.noteHistory = {};
            }

            if (!order.uiState.noteHistory[productId]) {
                order.uiState.noteHistory[productId] = [];
            }

            let added = false;
            for (const note of order.uiState.noteHistory[productId]) {
                if (note.lineId === selectedOrderline.id) {
                    note.new = inputNote;
                    added = true;
                }
            }
            if (!added) {
                order.uiState.noteHistory[productId].push({
                    old: oldNote,
                    new: inputNote || "",
                    lineId: selectedOrderline.id,
                    uuid: selectedOrderline.uuid,
                });
            }
        }
    },
});
