import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    async _applyParsedSync(resolved, deletionsByModel, opts = {}) {
        const incomingOrders = resolved["pos.order"] ?? [];
        const incomingUuids = new Set(incomingOrders.map((r) => r.uuid).filter(Boolean));

        // Snapshot pre-existing table orders that are NOT in the incoming payload.
        // After super, any of these whose table_id matches an incoming order is a duplicate.
        const preexisting = this.models["pos.order"]
            .filter((o) => !o.finalized && o.table_id && !incomingUuids.has(o.uuid))
            .map((o) => ({ uuid: o.uuid, tableId: o.table_id.id }));

        await super._applyParsedSync(resolved, deletionsByModel, opts);

        this._resolveTableDuplicates(incomingUuids, preexisting);
    },

    _resolveTableDuplicates(incomingUuids, preexisting) {
        if (!preexisting.length) {
            return;
        }

        // Build tableId → canonical model instance from the incoming orders (now in the store)
        const canonicalByTable = new Map();
        for (const uuid of incomingUuids) {
            const order = this.models["pos.order"].getBy("uuid", uuid);
            if (order && !order.finalized && order.table_id) {
                canonicalByTable.set(order.table_id.id, order);
            }
        }

        for (const { uuid, tableId } of preexisting) {
            const canonical = canonicalByTable.get(tableId);
            if (!canonical) {
                continue;
            }
            const dupe = this.models["pos.order"].getBy("uuid", uuid);
            if (!dupe || dupe.finalized) {
                continue;
            }
            for (const line of [...dupe.lines]) {
                line.update({ order_id: canonical });
            }
            this.models["pos.order"].deleteMany([dupe], { silent: true });
        }
    },
});
