import { ORM } from "@web/core/orm_plugin";
import { unique } from "@web/core/utils/arrays";
import { Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";

/**
 * @typedef {{
 *   deferred: PromiseWithResolvers;
 *   scheduled: boolean;
 *   ids: number[];
 * }} Batch
 */

export class BatchedOrmPlugin extends Plugin {
    static scoped(self, scope) {
        return Object.assign(Object.create(self), {
            read(...args) {
                return scope.run(() => self.read(...args));
            },
        });
    }

    /** @private */
    orm = usePlugin(ORM);

    /** @private @type {Record<string, Batch>} */
    batches = {};

    /**
     * @private
     * @param {number[]} ids
     * @param {any[]} keys
     * @param {Function} callback
     * @returns {Promise<any>}
     */
    async _batch(ids, keys, callback) {
        const key = JSON.stringify(keys);
        let batch = this.batches[key];
        if (!batch) {
            batch = {
                deferred: Promise.withResolvers(),
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

        return batch.deferred.promise;
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
        const records = await this._batch(resIds, ["read", resModel, fields, kwargs], (resIds) =>
            this.orm.read(resModel, resIds, fields, kwargs)
        );
        return records.filter((r) => resIds.includes(r.id));
    }
}
services.add(BatchedOrmPlugin);
