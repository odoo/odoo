import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async _setOrder(order) {
        const shouldBeOverridden = this.pos.config.module_pos_restaurant && order.table_id;
        if (!shouldBeOverridden) {
            return super._setOrder(...arguments);
        }
        // we came from the FloorScreen
        const orderTable = order.getTable();
        await this.pos.setTable(orderTable, order.uuid);
        this.closeTicketScreen();
    },
    async onDoRefund() {
        const order = this.getSelectedOrder();
        if (this.pos.config.module_pos_restaurant && order && !this.pos.selectedTable) {
            await this.pos.setTable(
                order.table ? order.table : this.pos.models["restaurant.table"].getAll()[0]
            );
        }
        await super.onDoRefund(...arguments);
    },
    isDefaultOrderEmpty(order) {
        if (this.pos.config.module_pos_restaurant) {
            return false;
        }
        return super.isDefaultOrderEmpty(...arguments);
    },
});
