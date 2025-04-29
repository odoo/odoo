import { useEnv } from "@odoo/owl";

export function useCachedModel() {
    return useEnv().editor.shared.cachedModel;
}

export class ModelEdit {
    constructor(history, model, recordId) {
        this.values = {};
        this.history = history;
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
    set(field, value) {
        const previous = this.values[field].current;
        value = JSON.stringify(value);
        this.history.applyCustomMutation({
            apply: () => {
                this.values[field].current = value;
            },
            revert: () => {
                this.values[field].current = previous;
            },
        });
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
