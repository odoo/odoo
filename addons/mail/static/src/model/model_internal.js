import { markRaw } from "@odoo/owl";
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
     * Names declared with `computed()`. Each record holds the
     * declaration as its own property until its first read replaces it with an
     * owl computed in `RecordInternal.fieldsComputed`.
     *
     * @type {Set<string>}
     */
    fieldsComputable = new Set();
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
