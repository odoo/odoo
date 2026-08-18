import { ATTR_SYM, MANY_SYM, ONE_SYM, untrackFunctions } from "./misc";
import { RecordInternal } from "@mail/model/record_internal";

import { markRaw } from "@odoo/owl";

export class ModelInternal {
    /** @type {typeof import("./record").Record} */
    RecordInternal = RecordInternal;
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
    /**
     *
     * @type {Set<string>}
     */
    /**
     * Names declared with `record.computed()`: the value is computed on the
     * first read and kept in an owl computed of its own, neither stored nor
     * serialized.
     *
     * @type {Set<string>}
     */
    fieldsComputable = new Set();
    /** @type {Map<string, string>} */
    fieldsInverse = new Map();
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
     *
     * @type {Map<string, string>}
     * */
    parentFields = new Map();

    constructor() {
        markRaw(this);
    }

    registerField(fieldName, data) {
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
            if (!["asProxy", "default", "html", "type"].includes(key) && data[ATTR_SYM]) {
                throw new Error(
                    `Unsupported option "${key}" on Attr field "${fieldName}". Attr fields only support "asProxy", "html" and "type".`
                );
            }
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
                case "inverse": {
                    this.fieldsInverse.set(fieldName, value);
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
}

untrackFunctions(ModelInternal.prototype, ["registerField"]);
