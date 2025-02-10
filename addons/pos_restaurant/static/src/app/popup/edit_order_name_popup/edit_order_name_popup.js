import { ListContainer } from "@point_of_sale/app/components/list_container/list_container";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class EditOrderNamePopup extends TextInputPopup {
    static template = "pos_restaurant.EditOrderNamePopup";
    static components = { ...super.components, ListContainer };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        super.setup();
    }
    transferOrder(order) {
        this.pos.transferOrder(this.currentOrder.uuid, null, order);
        this.pos.setOrder(order);
        this.dialog.closeAll();
    }
    get currentOrder() {
        return this.pos.getOrder();
    }
    get items() {
        return this.pos
            .getOpenOrders()
            .filter((o) => !o.table_id && o.uuid != this.currentOrder.uuid)
            .toSorted((a, b) => a.getName().localeCompare(b.getName()));
    }
}
