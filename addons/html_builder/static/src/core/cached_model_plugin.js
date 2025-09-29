import { Plugin } from "@html_editor/plugin";
import { Cache } from "@web/core/utils/cache";
import { ModelEdit } from "./cached_model_utils";

/**
 * @typedef { Object } CachedModelShared
 * @property { CachedModelPlugin['ormRead'] } ormRead
 * @property { CachedModelPlugin['ormSearchRead'] } ormSearchRead
 * @property { CachedModelPlugin['useModelEdit'] } useModelEdit
 */

export class CachedModelPlugin extends Plugin {
    static id = "cachedModel";
    static shared = ["ormRead", "ormSearchRead", "useModelEdit"];
    static dependencies = ["history"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        save_handlers: this.savePendingRecords.bind(this),
    };
    setup() {
        this.ormReadCache = new Cache(
            ({ model, ids, fields }) => this.services.orm.read(model, ids, fields),
            JSON.stringify
        );
        this.ormSearchReadCache = new Cache(
            ({ model, domain, fields }) => this.services.orm.searchRead(model, domain, fields),
            JSON.stringify
        );
        this.modelEditCache = new Cache(
            ({ model, recordId }) => new ModelEdit(this.dependencies.history, model, recordId),
            JSON.stringify
        );
    }
    destroy() {
        this.ormReadCache.invalidate();
        this.ormSearchReadCache.invalidate();
        this.modelEditCache.invalidate();
    }
    ormRead(model, ids, fields) {
        const SAFE_NULL = -1;
        const newIds = ids.map((id) => (id === null ? SAFE_NULL : id));
        return this.ormReadCache.read({ model, ids: newIds, fields });
    }
    ormSearchRead(model, domain, fields) {
        return this.ormSearchReadCache.read({ model, domain, fields });
    }
    useModelEdit({ model, recordId }) {
        const modelEdit = this.modelEditCache.read({ model, recordId });
        // track el ?
        return modelEdit;
    }
    async savePendingRecords() {
        const inventory = {}; // model => { recordId => { field => value } }
        for (const modelEdit of Object.values(this.modelEditCache.cache)) {
            modelEdit.collect(inventory);
        }
        // Save inventoried changes.
        const proms = [];
        for (const [model, records] of Object.entries(inventory)) {
            for (const [recordIdString, record] of Object.entries(records)) {
                for (const [field, value] of Object.entries(record)) {
                    const savePromise = Promise.all(
                        value.map(async (v) => {
                            if (typeof v.id === "string") {
                                const [id] = await this.services.orm.create(value.model, [
                                    { name: value.name },
                                ]);
                                return { ...value, id };
                            } else {
                                return v;
                            }
                        })
                    ).then(async (newValue) => {
                        const recordId = parseInt(recordIdString);
                        // Currently only ids selection values are supported.
                        await this.services.orm.write(model, [recordId], {
                            [field]: [[6, 0, newValue.map((v) => v.id)]],
                        });
                        this.modelEditCache
                            .read({ model, recordId })
                            .updateSavedValue(field, newValue);
                    });
                    proms.push(savePromise);
                }
            }
        }
        await Promise.all(proms);
        return !!inventory.length;
    }
}
