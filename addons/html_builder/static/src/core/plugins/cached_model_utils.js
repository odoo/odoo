import { useEnv } from "@odoo/owl";

export function useCachedModel() {
    return useEnv().editor.shared.CachedModel;
}

export class ModelEdit {
    constructor(editableEl) {
        this.editableEl = editableEl;
        // Keeps track of initial model values to handle browsing back in the
        // history beyond init.
        this.initialValues = {};
    }
    setRecord(model, recordId) {
        if (this.model) {
            // Reused
            if (model !== this.model || recordId !== this.recordId) {
                throw new Error(
                    `Incompatible record: ${model} ${recordId} vs ${this.model} ${this.recordId}`
                );
            }
            return;
        }
        this.model = model;
        this.recordId = recordId;
        this.selector = `[data-res-model="${this.model}"][data-res-id="${this.recordId}"]`;
    }
    getPropertyName(field) {
        return `_Edit${field[0].toUpperCase()}${field.slice(1)}`;
    }
    has(field) {
        return field in this.initialValues;
    }
    get(field) {
        const jsonValue = this.editableEl.querySelector(this.selector).dataset[
            this.getPropertyName(field)
        ];
        if (!jsonValue) {
            return this.initialValues[field];
        }
        return JSON.parse(jsonValue);
    }
    init(field, value) {
        this.initialValues[field] = value;
        this.set(field, value);
    }
    set(field, value) {
        const propertyName = this.getPropertyName(field);
        const textValue = JSON.stringify(value);
        for (const el of this.editableEl.querySelectorAll(this.selector)) {
            el.dataset[propertyName] = textValue;
        }
    }
    collect(inventory) {
        const records = inventory[this.model] || {};
        const record = records[this.recordId] || {};
        for (const field of Object.keys(this.initialValues)) {
            const textInitialValue = JSON.stringify(this.initialValues[field]);
            const propertyName = this.getPropertyName(field);
            const el = this.editableEl.querySelector(this.selector);
            if (el) {
                const textValue = el.dataset[propertyName];
                if (textValue !== textInitialValue) {
                    inventory[this.model] = records;
                    records[this.recordId] = record;
                    record[field] = JSON.parse(textValue);
                    for (const el of this.editableEl.querySelectorAll(this.selector)) {
                        delete el.dataset[propertyName];
                    }
                }
            }
        }
    }
}
