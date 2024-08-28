import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { groupBy } from "@web/core/utils/arrays";

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

    get availableFloor() {
        const groupedFloors = groupBy(this.tables, (t) => t.floor_id[0]);
        return Object.entries(groupedFloors).map(([floorId, tables]) => ({
            id: floorId,
            name: tables[0].floor_id[1],
            tables,
        }));
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
