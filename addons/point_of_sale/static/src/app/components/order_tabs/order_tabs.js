import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { ListContainer } from "@point_of_sale/app/generic_components/list_container/list_container";

export class OrderTabs extends Component {
    static template = "point_of_sale.OrderTabs";
    static components = {
        ListContainer,
    };
    static props = {
        orders: Array,
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
    }
    newFloatingOrder() {
        this.pos.selectedTable = null;
        this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
        this.dialog.closeAll();
    }
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.selectedTable = null;
        this.pos.showScreen("ProductScreen");
        this.dialog.closeAll();
    }
    get orders() {
        return this.props.orders.sort((a, b) => {
            // Orders with a note should be displayed first and alphabetically ordered
            if (a.note && !b.note) {
                return -1;
            } else if (!a.note && b.note) {
                return 1;
            } else if (a.note && b.note) {
                return a.note.localeCompare(b.note);
            }
        });
    }
}
