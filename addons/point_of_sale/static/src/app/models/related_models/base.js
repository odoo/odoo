import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";
import { deepImmutable, clone, RAW_SYMBOL } from "./utils";
import { toRaw } from "@odoo/owl";
const { DateTime } = luxon;

export class Base extends WithLazyGetterTrap {
    static excludedLazyGetters = ["id", "models"];

    constructor({ model, raw }) {
        super({});
        this.model = model;
        this[RAW_SYMBOL] = raw;
    }

    get models() {
        return this.model.models;
    }

    get id() {
        return this[RAW_SYMBOL].id;
    }

    get raw() {
        return deepImmutable(clone(this[RAW_SYMBOL]), "Raw data cannot be modified");
    }

    /**
     * Called during instantiation when the instance is fully-populated with field values.
     * This method is called when the instance is created or updated
     * @param {*} _vals
     */
    setup(_vals) {
        if (typeof this.id !== "number" && this.models._dirtyRecords[this.model.name]) {
            this.models._dirtyRecords[this.model.name].add(this.uuid);
            this._dirty = true;
        }
    }

    /**
     *  This method is invoked only during instance creation to preserve the state across updates.
     */
    initState() {}

    /**
     *  Restore state serialized from indexedDB
     */
    restoreState(uiState) {
        this.uiState = uiState;
    }

    isDirty() {
        return Boolean(this._dirty);
    }

    formatDateOrTime(field, type = "datetime") {
        if (type === "date") {
            return this[field].toLocaleString(DateTime.DATE_SHORT);
        }
        return this[field].toLocaleString(DateTime.DATETIME_SHORT);
    }

    isEqual(other) {
        return toRaw(this) === toRaw(other);
    }

    update(vals, opts = {}) {
        return this.model.update(this, vals, opts);
    }

    delete(opts = {}) {
        return this.model.delete(this, opts);
    }

    serializeForORM(opts = {}) {
        return this.model.serializeForORM(this, opts);
    }

    serializeForIndexedDB() {
        return this.model.serializeForIndexedDB(this);
    }

    serializeState() {
        if (!this.uiState) {
            return;
        }
        return { ...this.uiState };
    }

    backLink(link) {
        return this.model.backLink(this, link);
    }

    markDirty() {
        if (
            this.models._loadingData ||
            this._dirty ||
            !this.models._dirtyRecords[this.model.name]
        ) {
            return;
        }

        this._dirty = true;
        this.models._dirtyRecords[this.model.name].add(this.uuid);
        this.model.getParentFields().forEach((field) => {
            this[field.name]?.markDirty?.();
        });
    }

    unmarkDirty() {
        if (!this.models._dirtyRecords[this.model.name]) {
            return;
        }

        this.models._dirtyRecords[this.model.name].delete(this.uuid);
        this._dirty = false;
    }
}
