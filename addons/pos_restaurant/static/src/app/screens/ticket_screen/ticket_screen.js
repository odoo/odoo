import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getTable(order) {
        const table = order.getTable();
        if (table) {
            let floorAndTable = "";

            if (this.pos.models["restaurant.floor"].length > 0) {
                floorAndTable = `${table.floor_id.name}/`;
            }

            floorAndTable += table.getName();
            return floorAndTable;
        }
    },
    //@override
    _getSearchFields() {
        const res = super._getSearchFields(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            res.REFERENCE.modelFields.push("table_id.table_number");
        }
        return res;
    },
    async setOrder(order) {
        const shouldBeOverridden = this.pos.config.module_pos_restaurant && order.table_id;
        if (shouldBeOverridden) {
            const orderTable = order.getTable();
            await this.pos.setTable(orderTable, order.uuid);
        }
        return await super.setOrder(order);
    },
    isDefaultOrderEmpty(order) {
        if (this.pos.config.module_pos_restaurant) {
            return false;
        }
        return super.isDefaultOrderEmpty(...arguments);
    },
});
