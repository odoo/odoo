import { OrderlineNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/orderline_note_button/orderline_note_button";
export class GeneralNoteButton extends OrderlineNoteButton {
    static template = "point_of_sale.OrderlineNoteButton";
    static props = {
        ...OrderlineNoteButton.props,
    };
    async onClick() {
        const selectedOrder = this.pos.get_order();
        const selectedNote = selectedOrder.general_note || "";
        const payload = await this.openTextInput(selectedNote, true);
        selectedOrder.general_note = payload;
        return { confirmed: typeof payload === "string", inputNote: payload };
    }
}
