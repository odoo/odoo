import { useEnv } from "@web/owl2/utils";

export function useCachedModel() {
    return useEnv().editor.shared.cachedModel;
}

export class ModelEdit {
    constructor(model, recordId) {
        this.values = {};
        this.model = model;
        this.recordId = recordId;
    }
    has(field) {
        return field in this.values;
    }
    get(field) {
        return JSON.parse(this.values[field].current);
    }
    init(field, value) {
        value = JSON.stringify(value);
        this.values[field] = { initial: value, current: value };
    }
    /**
     * Set the value of a field. This is not an undoable change: edit fields
     * with `setFieldValue` of the cached model plugin.
     *
     * @param {string} field
     * @param {any} value
     */
    set(field, value) {
        this.values[field].current = JSON.stringify(value);
    }
    collect(inventory) {
        const records = inventory[this.model] || {};
        const record = records[this.recordId] || {};
        for (const field of Object.keys(this.values)) {
            if (this.values[field].initial !== this.values[field].current) {
                inventory[this.model] = records;
                records[this.recordId] = record;
                record[field] = JSON.parse(this.values[field].current);
            }
        }
    }
}
