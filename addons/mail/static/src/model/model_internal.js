import { ATTR_SYM, MANY_SYM, ONE_SYM, technicalKeysOnRecords, untrackFunctions } from "./misc";
import { Record } from "@mail/model/record";
import { RecordInternal } from "@mail/model/record_internal";

import { markRaw } from "@odoo/owl";

export class ModelInternal {
    /** @type {typeof import("./record").Record} */
    RecordInternal = RecordInternal;
    /**
     * The Model this internal belongs to, set by makeStore at creation.
     *
     * @type {typeof import("./record").Record}
     */
    Model;
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

    constructor(Model) {
        this.Model = Model;
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
        this.parentFields.delete(fieldName);
        const modelName = this.Model.getName();
        if (this.fieldsOne.get(fieldName) || this.fieldsMany.get(fieldName)) {
            const targetModel = this.fieldsTargetModel.get(fieldName);
            const OtherModel = this.Model.store.Models[targetModel];
            if (targetModel && !OtherModel) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            const inverse = this.fieldsInverse.get(fieldName);
            if (inverse) {
                const rel2TargetModel = OtherModel._.fieldsTargetModel.get(inverse);
                const rel2Inverse = OtherModel._.fieldsInverse.get(inverse);
                if (rel2TargetModel && rel2TargetModel !== modelName) {
                    throw new Error(
                        `Fields ${OtherModel.getName()}.${inverse} has wrong targetModel. Expected: "${modelName}" Actual: "${rel2TargetModel}"`
                    );
                }
                if (rel2Inverse && rel2Inverse !== fieldName) {
                    throw new Error(
                        `Fields ${OtherModel.getName()}.${inverse} has wrong inverse. Expected: "${fieldName}" Actual: "${rel2Inverse}"`
                    );
                }
                OtherModel._.fieldsTargetModel.set(inverse, modelName);
                OtherModel._.fieldsInverse.set(inverse, fieldName);
            }
        }
        if (Object.values(this.Model._inherits ?? {}).includes(fieldName)) {
            this.inheritsFields.add(fieldName);
            const inverse = this.fieldsInverse.get(fieldName);
            if (!inverse) {
                throw new Error(
                    `Missing inverse field of "${fieldName}" for _inherits in "${this.Model.getName()}"`
                );
            }
            const parentModelName = Object.keys(this.Model._inherits).find(
                (name) => this.Model._inherits[name] === fieldName
            );
            this.Model.store.Models[parentModelName]._.inheritsInverseFields.add(inverse);
        }
    }

    /**
     * The relation field `name` is read/written through to a parent, or
     * undefined when `name` is not inherited. Resolved on access (no up-front
     * parentFields build): `name` is inherited when this model does not own it
     * (no own field, nothing on its class prototype) and an _inherits parent
     * provides it, i.e. it is one of the parent's registered fields or a
     * getter/function on the parent's class prototype (a framework member on
     * Record.prototype is the record's own, not inherited). A positive result is
     * cached (a parent field, once it exists, stays); a negative is not (the
     * parent may register `name` later). Cleared for a field this model later
     * declares, from registerField.
     *
     * @param {string} name
     * @returns {string|undefined}
     */
    resolveParentField(name) {
        const inherits = this.Model._inherits;
        if (
            !inherits ||
            this.fields.has(name) ||
            this.fieldsComputable.has(name) ||
            technicalKeysOnRecords.has(name)
        ) {
            return undefined;
        }
        const cached = this.parentFields.get(name);
        if (cached) {
            return cached;
        }
        if (name in this.Model.prototype) {
            return undefined;
        }
        for (const parentModelName in inherits) {
            const ParentModel = this.Model.store.Models[parentModelName];
            let provides =
                ParentModel._.fields.has(name) || ParentModel._.fieldsComputable.has(name);
            for (
                let proto = ParentModel.prototype;
                !provides && proto && proto !== Record.prototype && proto !== Object.prototype;
                proto = Object.getPrototypeOf(proto)
            ) {
                const descriptor = Object.getOwnPropertyDescriptor(proto, name);
                if (descriptor) {
                    provides = Boolean(descriptor.get || typeof descriptor.value === "function");
                    break;
                }
            }
            if (provides) {
                const viaField = inherits[parentModelName];
                this.parentFields.set(name, viaField);
                return viaField;
            }
        }
        return undefined;
    }
}

untrackFunctions(ModelInternal.prototype, ["registerField"]);
