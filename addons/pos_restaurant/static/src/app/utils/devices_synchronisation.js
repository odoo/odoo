import DevicesSynchronisation from "@point_of_sale/app/utils/devices_synchronisation";
import { patch } from "@web/core/utils/patch";

patch(DevicesSynchronisation.prototype, {
    async processDynamicRecords(dynamicRecords) {
        const result = await super.processDynamicRecords(dynamicRecords);
        if (!dynamicRecords["pos.order"]?.length) {
            return result;
        }
        // Verify if there is only 1 order by table.
        const orderByTableId = this.models["pos.order"].reduce((acc, order) => {
            // Floating order doesn't need to be verified.
            if (!order.finalized && order.table_id?.id) {
                acc[order.table_id.id] = acc[order.table_id.id] || [];
                acc[order.table_id.id].push(order);
            }
            return acc;
        }, {});

        for (const orders of Object.values(orderByTableId)) {
            if (orders.length > 1) {
                // The only way to get here is if there is several waiters on the same table.
                // In this case we take orderline of the local order and we add it to the synced order.
                const localOrders = orders.filter((order) => !order.isSynced);
                const syncedOrder = orders
                    .filter((order) => order.isSynced)
                    .sort((a, b) => a.id - b.id);

                if (
                    (syncedOrder.length === 0 || localOrders.length === 0) &&
                    syncedOrder.length <= 1 &&
                    localOrders.length <= 1
                ) {
                    continue;
                }

                const uniqOrder = syncedOrder.pop();
                for (const order of [...localOrders, ...syncedOrder]) {
                    const linesIds = order.lines.map((line) => line.id);
                    for (const id of linesIds) {
                        order.models["pos.order.line"].get(id).update({
                            order_id: uniqOrder,
                        });
                    }
                }

                const localIds = [
                    ...localOrders.map((order) => order.uuid),
                    ...syncedOrder.map((order) => order.uuid),
                ];
                if (localIds.includes(this.pos.selectedOrderUuid)) {
                    this.pos.setOrder(uniqOrder);
                    this.pos.addPendingOrder([uniqOrder.id]);
                }

                await this.pos.deleteOrders([...syncedOrder, ...localOrders]);
            }
        }
    },
});
