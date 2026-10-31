import DevicesSynchronisation from "@point_of_sale/app/utils/devices_synchronisation";
import { patch } from "@web/core/utils/patch";

patch(DevicesSynchronisation.prototype, {
    async processDynamicRecords(dynamicRecords) {
        const processed = await super.processDynamicRecords(dynamicRecords);
        const order = this.pos.getOrder();
        if (
            order?.id &&
            order.payment_ids.some((p) => p.payment_method_id.type === "online") &&
            processed["pos.order"]?.some((o) => o.id === order.id)
        ) {
            this.pos.updateOnlinePaymentsDataWithServer(order, false);
        }
        return processed;
    },
});
