/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { loyaltyIdsGenerator } from "@pos_loyalty/overrides/models/pos_store";
import DevicesSynchronisation from "@point_of_sale/app/store/devices_synchronisation";

patch(DevicesSynchronisation.prototype, {
    setup(){
        super.setup(...arguments);
        this.coupons = {};
    },
    async setTable() {
        await super.setTable(...arguments);
        this.updateRewards();
    },
    readSerializedData(serializedCoupons) {
        const lines = this.models["pos.order.line"].filter(l => l.uuid in serializedCoupons);
        for (let uuid in serializedCoupons) {
            const matchingLine = lines.find(l => l?.uuid === uuid);
            if (matchingLine) {
                const {points, code, partner_id, program_id} = serializedCoupons[uuid];
                const coupon = this.pos.models["loyalty.card"].create({
                    id: loyaltyIdsGenerator(),
                    program_id: this.pos.models["loyalty.program"].get(program_id),
                    partner_id: this.pos.models["res.partner"].get(partner_id),
                    code,
                    points,
                });
                matchingLine.update({coupon_id: coupon});
            }
        }
    },
    async collect(data) {
        const res = await super.collect(...arguments)
        const { coupons } = data;
        this.coupons = coupons;
        return res;
    },
    processDynamicRecords() {
        const data = super.processDynamicRecords(...arguments);
        this.readSerializedData(this.coupons);

        return data;
    }
});
 