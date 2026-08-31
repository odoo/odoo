import { markRaw } from "@odoo/owl";
import { ATTR_SYM, MANY_SYM, ONE_SYM, technicalKeysOnRecords } from "./misc";
import { Record } from "@mail/model/record";

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

    /**
     * The model this internal belongs to, and every model of the store: the
     * registration reads both before the store record exists.
     *
     * @type {typeof Record}
     */
    Model;
    /** @type {Object<string, typeof Record>} */
    Models;
    /**
     * Whether the fields of the model are registered: the first record of the
     * model declares them from its setup(), the ones after find them there.
     *
     * @type {boolean}
     */
    fieldsPrepared = false;

    constructor(Model, Models) {
        this.Model = Model;
        this.Models = Models;
        markRaw(this);
    }

    /**
     * The field `name` is read and written through a parent, or undefined when
     * `name` is not inherited: this model does not own it (no field nor computed
     * of its own, no technical key, nothing on its class prototype) and a parent
     * provides it, as one of its registered fields or as a getter or function
     * on its class prototype (a framework member on Record.prototype is the
     * record's own). A positive answer is cached, a negative one is not: the
     * parent may register `name` later.
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
            const ParentModel = this.Models[parentModelName];
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

    /**
     * Register `fieldName` on the model, from the declaration of the first
     * record: it pairs the relation with its inverse and, when the field is an
     * _inherits relation, with its parent, which the boot loops did while every
     * field was known up front.
     *
     * @param {string} fieldName
     * @param {any} data the field definition
     */
    registerField(fieldName, data) {
        this.prepareField(fieldName, data);
        // a name this model now owns is no longer read through a parent
        this.parentFields.delete(fieldName);
        const modelName = this.Model.getName();
        if (this.fieldsOne.get(fieldName) || this.fieldsMany.get(fieldName)) {
            const targetModel = this.fieldsTargetModel.get(fieldName);
            const OtherModel = this.Models[targetModel];
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
                // FIXME: lazy fields are not working properly with inverse.
                this.fieldsEager.set(fieldName, true);
                OtherModel._.fieldsEager.set(inverse, true);
            }
        }
        if (Object.values(this.Model._inherits ?? {}).includes(fieldName)) {
            this.inheritsFields.add(fieldName);
            const inverse = this.fieldsInverse.get(fieldName);
            if (!inverse) {
                throw new Error(
                    `Missing inverse field of "${fieldName}" for _inherits in "${modelName}"`
                );
            }
            const parentModelName = Object.keys(this.Model._inherits).find(
                (name) => this.Model._inherits[name] === fieldName
            );
            this.Models[parentModelName]._.inheritsInverseFields.add(inverse);
        }
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
