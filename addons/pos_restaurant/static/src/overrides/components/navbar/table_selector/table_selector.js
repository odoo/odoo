import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";

export class TableSelector extends NumberPopup {
    static template = "pos_restaurant.TableSelector";
    static components = { ...super.components, OrderTabs };
    setup() {
        this.pos = usePos();
        super.setup();
    }
}
