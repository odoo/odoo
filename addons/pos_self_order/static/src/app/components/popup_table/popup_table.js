import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class PopupTable extends Component {
    static template = "pos_self_order.PopupTable";
    static props = { selectTable: Function };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.state = useState({
            selectedTable: "0",
        });
    }

    setTable() {
        const table = this.selectedTable;

        if (!table) {
            return;
        }

        this.props.selectTable(table);
    }

    close() {
        this.props.selectTable(null);
    }

    get validSelection() {
        return Boolean(this.selectedTable);
    }

    get selectedTable() {
        return this.selfOrder.models["restaurant.table"].get(this.state.selectedTable);
    }
}
