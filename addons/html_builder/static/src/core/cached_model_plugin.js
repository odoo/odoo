import { Plugin } from "@html_editor/plugin";
import { Cache } from "@web/core/utils/cache";
import { ModelEdit } from "./cached_model_utils";

export class CachedModelPlugin extends Plugin {
    static id = "cachedModel";
    static shared = ["ormRead", "ormSearchRead", "useModelEdit"];
    static dependencies = ["history"];
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
    useModelEdit({ model, recordId, field }) {
        const modelEdit = this.modelEditCache.read({ model, recordId, field });
        // track el ?
        return modelEdit;
    }
    async savePendingRecords() {
        const inventory = {}; // model => { recordId => { field => value } }
        for (const modelEdit of Object.values(this.modelEditCache.cache)) {
            modelEdit.collect(inventory);
        }
        // Save inventoried changes.
        for (const [model, records] of Object.entries(inventory)) {
            for (const [recordId, record] of Object.entries(records)) {
                for (const [field, value] of Object.entries(record)) {
                    // Currently only ids selection values are supported.
                    const proms = value
                        .filter((value) => typeof value.id === "string")
                        .map((value) =>
                            this.services.orm.create(value.model, [{ name: value.name }])
                        );
                    const createdIDs = (await Promise.all(proms)).flat();
                    const ids = value
                        .filter((value) => typeof value.id === "number")
                        .map((value) => value.id)
                        .concat(createdIDs);
                    await this.services.orm.write(model, [parseInt(recordId)], {
                        [field]: [[6, 0, ids]],
                    });
                }
            }
        }
        return !!inventory.length;
    }
}
