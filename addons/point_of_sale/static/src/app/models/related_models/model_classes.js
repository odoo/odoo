import {
    RELATION_TYPES,
    DATE_TIME_TYPE,
    X2MANY_TYPES,
    RAW_SYMBOL,
    convertRawToDateTime,
    STORE_SYMBOL,
} from "./utils";
import { Base } from "./base";

/**
 * Processes model definitions to dynamically define getter and setter properties
 * on model fields, providing controlled access to the raw data.
 */
export function processModelClasses(modelDefs, modelClasses = {}) {
    for (const modelName in modelDefs) {
        const fields = modelDefs[modelName];
        const ModelRecordClass = modelClasses[modelName] || class ModelRecord extends Base {};
        modelClasses[modelName] = ModelRecordClass;
        const simpleGetters = [];

        for (const fieldName in fields) {
            const field = fields[fieldName];
            if (field.dummy || fieldName === "id") {
                continue;
            }
            if (fieldName in ModelRecordClass.prototype) {
                throw new Error(
                    `The property "${fieldName}" defined in the class "${ModelRecordClass.name}" matches an existing model "${modelName}" property. Please use a different property name.`
                );
            }
            if (!RELATION_TYPES.has(field.type) || !(field.relation in modelDefs)) {
                if (!DATE_TIME_TYPE.has(field.type)) {
                    simpleGetters.push(fieldName);
                }
                Object.defineProperty(ModelRecordClass.prototype, fieldName, {
                    get: function () {
                        const value = this[RAW_SYMBOL][fieldName];
                        if (DATE_TIME_TYPE.has(field.type)) {
                            return convertRawToDateTime(this, value, field);
                        }
                        return value;
                    },
                    set: function (newValue) {
                        this.update({ [fieldName]: newValue });
                    },
                    enumerable: true,
                });
            } else {
                const relationModel = field.relation;
                const updateErrorMessage = `Property '${fieldName}' of '${relationModel}' cannot be directly modified. Use the update method instead.`;
                if (X2MANY_TYPES.has(field.type)) {
                    Object.defineProperty(ModelRecordClass.prototype, fieldName, {
                        get: function () {
                            const ids = this[RAW_SYMBOL][fieldName] || [];
                            return unmodifiableArray(
                                ids
                                    .map((recordID) =>
                                        this[STORE_SYMBOL].getById(relationModel, recordID)
                                    )
                                    .filter((s) => s), //avoid empty records,
                                updateErrorMessage
                            );
                        },
                        set: function (newValue) {
                            if (field.dummy) {
                                throw new Error(updateErrorMessage);
                            }
                            this.update({ [fieldName]: newValue }, { fireFieldUpdate: true });
                        },
                        enumerable: true,
                    });
                } else if (field.type === "many2one") {
                    Object.defineProperty(ModelRecordClass.prototype, fieldName, {
                        get: function () {
                            const id = this[RAW_SYMBOL][fieldName];
                            if (!id) {
                                return undefined;
                            }
                            return this[STORE_SYMBOL].getById(relationModel, id);
                        },
                        set: function (newValue) {
                            if (field.dummy) {
                                throw new Error(updateErrorMessage);
                            }
                            this.update({ [fieldName]: newValue }, { fireFieldUpdate: true });
                        },
                        enumerable: true,
                    });
                }
            }
        }
        if (simpleGetters.length > 0) {
            ModelRecordClass.excludedLazyGetters = [
                ...ModelRecordClass.excludedLazyGetters,
                ...simpleGetters,
            ];
        }
    }
}

function unmodifiableArray(arr, message) {
    return new Proxy(arr, {
        set(target, prop, value) {
            throw new Error(message);
        },
        deleteProperty(target, prop) {
            throw new Error(message);
        },
        defineProperty(target, prop, descriptor) {
            throw new Error(message);
        },
        get(target, prop, receiver) {
            return Reflect.get(target, prop, receiver);
        },
    });
}

export function computeBackLinks(field) {
    const isOneToMany = field.type === "one2many";
    return function () {
        // "this" is reactive instance
        const result = [];
        this[STORE_SYMBOL].forEachRecord(field.relation, "id", (rec) => {
            const values = rec[RAW_SYMBOL][field.inverse_name];
            if (!values) {
                return;
            }
            if (isOneToMany ? values === this.id : values.includes(this.id)) {
                result.push(rec);
            }
        });
        return result || [];
    };
}
