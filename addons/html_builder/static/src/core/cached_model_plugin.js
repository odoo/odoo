import { Plugin } from "@html_editor/plugin";
import { Cache } from "@web/core/utils/cache";
import { ModelEdit } from "./cached_model_utils";

/**
 * @typedef { Object } CachedModelShared
 * @property { CachedModelPlugin['ormRead'] } ormRead
 * @property { CachedModelPlugin['ormSearchRead'] } ormSearchRead
 * @property { CachedModelPlugin['useModelEdit'] } useModelEdit
 * @property { CachedModelPlugin['setFieldValue'] } setFieldValue
 */

/**
 * @typedef {(data: {
 *     model: string,
 *     recordId: number,
 *     field: string,
 *     before: any,
 *     after: any,
 * }) => void} cached_model
 */

export class CachedModelPlugin extends Plugin {
    static id = "cachedModel";
    static shared = ["ormRead", "ormSearchRead", "useModelEdit", "setFieldValue"];
    static dependencies = ["history"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        history_data_properties: {
            cached_model: {
                apply: ({ model, recordId, field, after }) =>
                    this.useModelEdit({ model, recordId }).set(field, after),
                revert: ({ model, recordId, field, before }) =>
                    this.useModelEdit({ model, recordId }).set(field, before),
            },
        },
        on_ready_to_save_document_handlers: this.savePendingRecords.bind(this),
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
            ({ model, recordId }) => new ModelEdit(model, recordId),
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
    /**
     * Set the value of a field of a record, as an undoable change.
     *
     * @param {Object} params
     * @param {string} params.model
     * @param {number} params.recordId
     * @param {string} params.field
     * @param {any} params.value
     */
    setFieldValue({ model, recordId, field, value }) {
        this.dependencies.history.apply("cached_model", {
            model,
            recordId,
            field,
            before: this.useModelEdit({ model, recordId }).get(field),
            // The value can come from reactive state, which cannot be cloned:
            // keep the plain data that the record stores.
            after: JSON.parse(JSON.stringify(value)),
        });
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
