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

    get isSynced() {
        return typeof this.id === "number";
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
        this._dirty = !this.isSynced;
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
        return this._dirty;
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

    _markDirty() {
        if (this.models._loadingData || this._dirty) {
            return;
        }

        this._dirty = true;
        this.model.getParentFields().forEach((field) => {
            this[field.name]?._markDirty?.();
        });
    }
}
