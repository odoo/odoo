import { registry } from "@web/core/registry";
import { ORM } from "@web/core/orm_plugin";
import { unique } from "@web/core/utils/arrays";

class RequestBatcherORM extends ORM {
    constructor() {
        super();
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
    async batch(ids, keys, callback, onRefresh) {
        const key = JSON.stringify(keys);
        let batch = this.batches[key];
        if (!batch) {
            batch = {
                deferred: Promise.withResolvers(),
                scheduled: false,
                ids: [],
                refreshCallbacks: [],
            };
            this.batches[key] = batch;
        }
        batch.ids = unique([...batch.ids, ...ids]);
        if (onRefresh) {
            batch.refreshCallbacks.push(onRefresh);
        }

        if (!batch.scheduled) {
            batch.scheduled = true;
            Promise.resolve().then(async () => {
                delete this.batches[key];
                let result;
                try {
                    result = await callback(batch.ids, batch.refreshCallbacks);
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
     * Reads with different cache settings are never batched together. When the
     * cache `callback` option is used, it is called with the fresh records of
     * the given ids only.
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {string[]} fields
     * @returns {Promise<Object[]>}
     */
    async read(resModel, resIds, fields, kwargs) {
        const { callback, ...cacheOptions } = this._cache || {};
        const onRefresh =
            callback &&
            ((freshRecords, hasChanged) =>
                callback(
                    freshRecords.filter((r) => resIds.includes(r.id)),
                    hasChanged
                ));
        const records = await this.batch(
            resIds,
            ["read", resModel, fields, kwargs, this._cache ? cacheOptions : false],
            (allIds, refreshCallbacks) => {
                const orm = this._cache
                    ? this.unscoped.cache({
                          ...cacheOptions,
                          callback: (freshRecords, hasChanged) =>
                              refreshCallbacks.forEach((cb) => cb(freshRecords, hasChanged)),
                      })
                    : this.unscoped;
                return super.read.call(orm, resModel, allIds, fields, kwargs);
            },
            onRefresh
        );
        return records.filter((r) => resIds.includes(r.id));
    }
}

export const batchedOrmService = {
    async: [
        "call",
        "create",
        "nameGet",
        "read",
        "formattedReadGroup",
        "search",
        "searchRead",
        "unlink",
        "webSearchRead",
        "write",
    ],
    start() {
        return new RequestBatcherORM();
    },
};

registry.category("services").add("batchedOrm", batchedOrmService);
