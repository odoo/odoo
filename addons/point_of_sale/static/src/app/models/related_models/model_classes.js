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
    const modelNames = new Set(Object.keys(modelDefs));
    for (const modelName of modelNames) {
        const fields = modelDefs[modelName];
        const ModelRecordClass = modelClasses[modelName] || class ModelRecord extends Base {};
        modelClasses[modelName] = ModelRecordClass;
        const excludedLazyGetters = [];

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
            const isRelationNotInModelDef = field.relation && !modelNames.has(field.relation);
            if (!RELATION_TYPES.has(field.type) || isRelationNotInModelDef) {
                const isDateTime = DATE_TIME_TYPE.has(field.type);
                if (!isDateTime) {
                    excludedLazyGetters.push(fieldName);
                }
                Object.defineProperty(ModelRecordClass.prototype, fieldName, {
                    get: function () {
                        const value = this[RAW_SYMBOL][fieldName];
                        if (isDateTime) {
                            return convertRawToDateTime(this, value, field);
                        } else if (isRelationNotInModelDef && value instanceof Set) {
                            return unmodifiableArray(
                                [...value],
                                `The '${fieldName}' array cannot be modified.`
                            );
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
                const updateErrorMessage = `The '${fieldName}' array cannot be modified. Use the update method instead.`;
                if (X2MANY_TYPES.has(field.type)) {
                    Object.defineProperty(ModelRecordClass.prototype, fieldName, {
                        get: function () {
                            return unmodifiableArray(
                                Array.from(this[RAW_SYMBOL][fieldName] || new Set(), (recordID) =>
                                    this[STORE_SYMBOL].getById(relationModel, recordID)
                                ).filter((s) => s), //avoid empty records,
                                updateErrorMessage
                            );
                        },
                        set: function (values) {
                            this.update({ [fieldName]: values });
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
                            this.update({ [fieldName]: newValue });
                        },
                        enumerable: true,
                    });
                }
            }
        }
        if (excludedLazyGetters.length > 0) {
            ModelRecordClass.excludedLazyGetters = [
                ...ModelRecordClass.excludedLazyGetters,
                ...excludedLazyGetters,
            ];
        }
    }
}
export function createExtraField(record, extraFields, serverData, vals) {
    if (!extraFields?.length) {
        return;
    }
    if (!serverData) {
        // Assign the value to the instance (not in raw data)
        for (let i = 0; i < extraFields.length; i++) {
            const field = extraFields[i];
            record[field] = vals[field];
        }
        return;
    }
    // Create raw data shortcuts getter for the given fields
    for (let i = 0; i < extraFields.length; i++) {
        const fieldName = extraFields[i];
        if (fieldName in record) {
            continue;
        }
        Object.defineProperty(record, fieldName, {
            get: function () {
                const value = this[RAW_SYMBOL][fieldName];
                if (Array.isArray(value)) {
                    return unmodifiableArray(value, `The '${fieldName}' array cannot be modified`);
                }
                return value;
            },
            set: function (newValue) {
                throw new Error(`${fieldName} is read-only`);
            },
            enumerable: true,
        });
    }
}

/**
 * Returns a function that computes backlinks for a given field.
 * This function iterates over related records and returns those that reference the current record's ID.
 */
export function computeBackLinks(field) {
    const isOneToMany = field.type === "one2many";
    return function () {
        // "this" is reactive instance
        const result = [];
        const recordsMap = this[STORE_SYMBOL].getRecordsMap(field.relation, "id");
        for (const record of recordsMap.values()) {
            const values = record[RAW_SYMBOL][field.inverse_name];
            if (!values) {
                continue;
            }
            if (isOneToMany ? values === this.id : values.has(this.id)) {
                result.push(record);
            }
        }
        return result || [];
    };
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
