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
    setRecord(model, id) {
        if (this.model) {
            // Reused
            if (model !== this.model || id !== this.id) {
                throw new Error(`Incompatible record: ${model} ${id} vs ${this.model} ${this.id}`);
            }
            return;
        }
        this.model = model;
        this.id = id;
        this.selector = `[data-res-model="${this.model}"][data-res-id="${this.id}"]`;
    }
    getPropertyName(key) {
        return `_Edit${key[0].toUpperCase()}${key.slice(1)}`;
    }
    has(key) {
        return key in this.initialValues;
        // return this.getPropertyName(key) in this.editableEl.querySelector(this.selector).dataset;
    }
    get(key) {
        const jsonValue = this.editableEl.querySelector(this.selector).dataset[
            this.getPropertyName(key)
        ];
        if (!jsonValue) {
            return this.initialValues[key];
        }
        return JSON.parse(jsonValue);
    }
    init(key, value) {
        this.initialValues[key] = value;
        this.set(key, value);
    }
    set(key, value) {
        const propertyName = this.getPropertyName(key);
        const textValue = JSON.stringify(value);
        for (const el of this.editableEl.querySelectorAll(this.selector)) {
            el.dataset[propertyName] = textValue;
        }
    }
}
