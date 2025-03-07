import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";
import { deepImmutable, clone, RAW_SYMBOL } from "./utils";
import { toRaw } from "@odoo/owl";
const { DateTime } = luxon;

export class Base extends WithLazyGetterTrap {
    static excludedLazyGetters = ["id", "models"];

    constructor({ model, raw, traps }) {
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
        this._dirty = typeof this.id !== "number";
    }

    /**
     *  This method is invoked only during instance creation to preserve the state across updates.
     */
    initState() {}

    _markDirty(fieldName) {
        if (this.models._loadingData || this._dirty || fieldName?.startsWith("<-")) {
            return;
        }

        this._dirty = true;
        this.model.getParentFields().forEach((field) => {
            this[field.name]?._markDirty?.();
        });
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

    serializeState() {
        return { ...this.uiState };
    }

    restoreState(vals) {
        // Restore state serialized by the data service
        this.uiState = vals;
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

    serialize(opts = {}) {
        if (opts.orm) {
            return this.model.serializeForORM(this, opts);
        }
        return { ...this.raw };
    }

    backLink(link) {
        return this.model.backLink(this, link);
    }
}
