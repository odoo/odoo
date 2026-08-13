import { markRaw, toRaw } from "@odoo/owl";
import { ATTR_SYM, MANY_SYM, ONE_SYM } from "./misc";

export class ModelInternal {
    /** @type {Map<string, boolean>} */
    fields = new Map();
    /** @type {Map<string, boolean>} */
    fieldsAttr = new Map();
    /** @type {Map<string, boolean>} */
    fieldsOne = new Map();
    /** @type {Map<string, boolean>} */
    fieldsMany = new Map();
    /** @type {Map<string, boolean>} */
    fieldsHtml = new Map();
    /** @type {Map<string, string>} */
    fieldsTargetModel = new Map();
    /** @type {Map<string, () => Function[]>} */
    fieldsCompute = new Map();
    /** @type {Map<string, boolean>} */
    fieldsEager = new Map();
    /**
     * Which fields keep their value in an owl `computed()`, instead of the
     * model scheduling the compute and storing it. Only a lazy field holding
     * a plain value qualifies, as every other kind needs the stored value
     * itself:
     * - a relation has to materialize in its RecordList, which holds the inverse,
     * - an eager field is recomputed even while nobody reads it,
     * - an html, date or datetime value is converted on write,
     * - a localStorage field is read back from the storage,
     * - a compute reading the field it computes has no starting value to read.
     * Key is fieldName.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputable = new Map();
    /** @type {Map<string, string>} */
    fieldsInverse = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnAdd = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnDelete = new Map();
    /** @type {Map<string, Array<() => void>>} */
    fieldsOnUpdate = new Map();
    /** @type {Map<string, string>} */
    fieldsType = new Map();
    /** @type {Set<string>} */
    fieldsLocalStorage = new Set();
    /**
     * Fields whose value is mutated in place, so a read returns it as a proxy.
     *
     * @type {Set<string>}
     */
    fieldsAttrAsProxy = new Set();
    /**
     * Set of field names on the current model that are _inherits fields.
     *
     * @type {Set<string>}
     */
    inheritsFields = new Set();
    /**
     * Set of field names on the current model that are the inverse of _inherits fields.
     *
     * @type {Set<string>}
     */
    inheritsInverseFields = new Set();
    /**
     * Map of field name to the name of the relation field through which this field should be read.
     *
     * @type {Map<string, string>}
     * */
    parentFields = new Map();

    constructor() {
        markRaw(this);
    }

    prepareField(fieldName, data) {
        this.fields.set(fieldName, true);
        if (data[ATTR_SYM]) {
            this.fieldsAttr.set(fieldName, true);
        }
        if (data[ONE_SYM]) {
            this.fieldsOne.set(fieldName, true);
        }
        if (data[MANY_SYM]) {
            this.fieldsMany.set(fieldName, true);
        }
        if (data.localStorage) {
            if (data.compute) {
                throw new Error(
                    `The field "${fieldName}" cannot have "localStorage" and "compute" at the same time. "localStorage" is implicitly a computed field`
                );
            }
            this.fieldsLocalStorage.add(fieldName);
            this.fieldsCompute.set(
                fieldName,
                /** @this {import("./record").Record}*/
                function fieldLocalStorageCompute() {
                    const record = toRaw(this)._raw;
                    const lse = record._.fieldsLocalStorage.get(fieldName);
                    const value = lse.get();
                    if (value === undefined) {
                        if (!this._rawStore._.isUpdatingFromStorageEvent) {
                            lse.remove();
                        }
                        return this[fieldName];
                    }
                    return value;
                }
            );

            this.registerOnUpdate(
                fieldName,
                /** @this {import("./record").Record}*/
                function fieldLocalStorageOnChange(value) {
                    const record = toRaw(this)._raw;
                    if (this._rawStore._.isUpdatingFromStorageEvent) {
                        return;
                    }
                    const lse = record._.fieldsLocalStorage.get(fieldName);
                    if (value === record._.fieldsDefault.get(fieldName)) {
                        lse.remove();
                    } else {
                        lse.set(value);
                    }
                }
            );
        }
        for (const key in data) {
            const value = data[key];
            switch (key) {
                case "html": {
                    if (!value) {
                        break;
                    }
                    this.fieldsHtml.set(fieldName, value);
                    break;
                }
                case "targetModel": {
                    this.fieldsTargetModel.set(fieldName, value);
                    break;
                }
                case "compute": {
                    this.fieldsCompute.set(fieldName, value);
                    break;
                }
                case "eager": {
                    if (!value) {
                        break;
                    }
                    this.fieldsEager.set(fieldName, value);
                    break;
                }
                case "inverse": {
                    this.fieldsInverse.set(fieldName, value);
                    break;
                }
                case "onAdd": {
                    this.fieldsOnAdd.set(fieldName, value);
                    break;
                }
                case "onDelete": {
                    this.fieldsOnDelete.set(fieldName, value);
                    break;
                }
                case "onUpdate": {
                    this.registerOnUpdate(fieldName, value);
                    break;
                }
                case "asProxy": {
                    if (!value) {
                        break;
                    }
                    this.fieldsAttrAsProxy.add(fieldName);
                    break;
                }
                case "type": {
                    this.fieldsType.set(fieldName, value);
                    break;
                }
            }
        }
        const compute = this.fieldsCompute.get(fieldName);
        const type = this.fieldsType.get(fieldName);
        this.fieldsComputable.set(
            fieldName,
            Boolean(compute) &&
                !this.fieldsEager.get(fieldName) &&
                !this.fieldsOne.get(fieldName) &&
                !this.fieldsMany.get(fieldName) &&
                !this.fieldsHtml.get(fieldName) &&
                type !== "date" &&
                type !== "datetime" &&
                !this.fieldsLocalStorage.has(fieldName) &&
                !new RegExp(`this\\.${fieldName}\\b`).test(compute.toString())
        );
    }
    registerOnUpdate(fieldName, onUpdate) {
        let onUpdateList = this.fieldsOnUpdate.get(fieldName);
        if (!onUpdateList) {
            onUpdateList = [];
            this.fieldsOnUpdate.set(fieldName, onUpdateList);
        }
        onUpdateList.push(onUpdate);
    }
}
