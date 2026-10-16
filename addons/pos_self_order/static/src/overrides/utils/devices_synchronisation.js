import DevicesSynchronisation from "@point_of_sale/app/utils/devices_synchronisation";
import { patch } from "@web/core/utils/patch";

patch(DevicesSynchronisation.prototype, {
    async processDynamicRecords(dynamicRecords) {
        const processed = await super.processDynamicRecords(dynamicRecords);
        if (!processed["pos.order"]?.length) {
            return processed;
        }

        const paidSelfOrder = processed["pos.order"].filter(
            (o) => ["paid", "done"].includes(o.state) && ["mobile", "kiosk"].includes(o.source)
        );

        for (const order of paidSelfOrder) {
            this.displayNotification(order);
        }
    },
});
