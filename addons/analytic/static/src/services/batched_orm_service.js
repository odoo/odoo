/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ORM } from "@web/core/orm_service";
import { unique } from "@web/core/utils/arrays";
import { Deferred } from "@web/core/utils/concurrency";

class RequestBatcherORM extends ORM {
    constructor() {
        super(...arguments);
        this.searchReadBatches = {};
        this.searchReadBatchId = 1;
        this.batches = {};
    }

    /**
     * @param {number[]} ids
     * @param {any[]} keys
     * @param {Function} callback
     * @returns {Promise<any>}
     */
    async batch(ids, keys, callback) {
        const key = JSON.stringify(keys);
        let batch = this.batches[key];
        if (!batch) {
            batch = {
                deferred: new Deferred(),
                scheduled: false,
                ids: [],
            };
            this.batches[key] = batch;
        }
        batch.ids = unique([...batch.ids, ...ids]);

        if (!batch.scheduled) {
            batch.scheduled = true;
            Promise.resolve().then(async () => {
                delete this.batches[key];
                let result;
                try {
                    result = await callback(batch.ids);
                } catch (e) {
                    return batch.deferred.reject(e);
                }
                batch.deferred.resolve(result);
            });
        }

        return batch.deferred;
    }

    /**
     * Entry point to batch "read" calls. If the `fields` and `resModel`
     * arguments have already been called, the given ids are added to the
     * previous list of ids to perform a single read call. Once the server
     * responds, records are then dispatched to the callees based on the
     * given ids arguments (kept in the closure).
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {string[]} fields
     * @returns {Promise<Object[]>}
     */
    async read(resModel, resIds, fields, kwargs) {
        const records = await this.batch(resIds, ["read", resModel, fields, kwargs], (resIds) =>
            super.read(resModel, resIds, fields, kwargs)
        );
        return records.filter((r) => resIds.includes(r.id));
    }
}

export const batchedOrmService = {
    dependencies: ["rpc", "user"],
    async: [
        "call",
        "create",
        "nameGet",
        "read",
        "readGroup",
        "search",
        "searchRead",
        "unlink",
        "webSearchRead",
        "write",
    ],
    start(env, { rpc, user }) {
        return new RequestBatcherORM(rpc, user);
    },
};

registry.category("services").add("batchedOrm", batchedOrmService);
