import { PgSnapshot } from "@mail/model/field_version";
import { Record } from "./record";
import { STORE_SYM, untrackFunctions } from "./misc";

/** @typedef {import("./record_list").RecordList} RecordList */

export class Store extends Record {
    static singleton = true;
    /** @type {import("./store_internal").StoreInternal} */
    _;
    get [STORE_SYM]() {
        return true;
    }

    handleError(err) {
        this._.ERRORS.push(err);
    }

    /**
     * @template T
     * @param {T & {__store_version__?: import("@mail/model/field_version").StoreVersion}} [dataByModelName={}]
     * @param {Object} [options={}]
     * @returns {{ [K in keyof T]: import("models").Models[K][] }}
     */
    insert(dataByModelName = {}, options = {}) {
        const store = this;
        // Only cleanup if we initiated the insert.
        const shouldCleanup = !this._.currentInsertVersion;
        if ("__store_version__" in dataByModelName) {
            const versionMeta = dataByModelName.__store_version__;
            delete dataByModelName.__store_version__;
            // Only consider the new "xip_list" format. Older payloads are applied
            // unversioned.
            this._.currentInsertVersion = versionMeta.snapshot.xip_list
                ? { ...versionMeta, snapshot: new PgSnapshot(versionMeta.snapshot) }
                : null;
        }
        try {
            this._.MAKE_UPDATE(function storeInsert() {
                const recordsDataToDelete = [];
                for (const [modelName, data] of Object.entries(dataByModelName)) {
                    if (!store[modelName]) {
                        console.warn(
                            `store.insert() received data for unknown model “${modelName}”.`
                        );
                        continue;
                    }
                    const insertData = [];
                    for (const vals of Array.isArray(data) ? data : [data]) {
                        if (vals._DELETE) {
                            delete vals._DELETE;
                            recordsDataToDelete.push([modelName, vals]);
                        } else {
                            insertData.push(vals);
                        }
                    }
                    store[modelName].insert(insertData, options);
                }
                // Delete after all inserts to make sure a relation potentially registered before the
                // delete doesn't re-add the deleted record by mistake.
                for (const [modelName, vals] of recordsDataToDelete) {
                    store[modelName].get(vals)?.delete();
                }
            });
        } finally {
            if (shouldCleanup) {
                this._.currentInsertVersion = null;
            }
        }
    }
}

untrackFunctions(Store.prototype, ["handleError", "insert"]);
