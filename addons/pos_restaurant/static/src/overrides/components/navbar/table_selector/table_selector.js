import { usePos } from "@point_of_sale/app/store/pos_hook";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

export class TableSelector extends NumberPopup {
    static template = "pos_restaurant.TableSelector";
    static components = { ...super.components, OrderTabs };
    setup() {
        this.pos = usePos();
        super.setup();
    }
}
