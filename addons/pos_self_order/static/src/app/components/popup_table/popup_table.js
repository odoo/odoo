/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { groupBy } from "@web/core/utils/arrays";

export class PopupTable extends Component {
    static template = "pos_self_order.PopupTable";
    static props = { selectTable: Function };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.rpc = useService("rpc");
        this.tables = [];
        this.state = useState({
            selectedTable: null,
        });

        onWillStart(async () => {
            await this.getTable();
        });
    }

    async getTable() {
        try {
            this.tables = await this.rpc("/pos-self-order/get-tables", {
                access_token: this.selfOrder.access_token,
            });
        } catch (e) {
            this.selfOrder.handleErrorNotification(e);
        }

        this.state.selectedTable = this.tables[0]?.id;
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
        const table = this.tables.find((t) => t.id === parseInt(this.state.selectedTable));
        this.props.selectTable(table);
    }

    close() {
        this.props.selectTable(null);
    }
}
