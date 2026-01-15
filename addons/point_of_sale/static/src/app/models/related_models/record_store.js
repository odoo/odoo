import { Base } from "./base";
import { RAW_SYMBOL } from "./utils";
import { reactive } from "@odoo/owl";

export class RecordStore {
    /**
     * @param {Array<string>} models - List of model names to register.
     * @param {object} indexes - A map from model name to an array of index keys.
     */
    constructor(models, indexes = {}) {
        this.indexes = {};
        this.records = new Map();

        models.forEach((model) => {
            const modelMap = new Map();
            this.records.set(model, modelMap);
            const indexKeys = new Set([...(indexes[model] || []).filter((s) => s), "id"]);
            this.indexes[model] = indexKeys;
            for (const key of indexKeys) {
                modelMap.set(key, new Map());
            }
        });
        return reactive(this);
    }

    /**
     * Adds a record
     * @param {Base} record - An instance of Base.
     */
    add(record) {
        return this._updateIndex(record, (map, key, record, isArray = false) => {
            if (isArray) {
                if (!map.has(key)) {
                    map.set(key, new Map([[record.id, record]]));
                } else {
                    map.get(key).set(record.id, record);
                }
            } else {
                map.set(key, record);
            }
        });
    }

    /**
     * Removes a record
     * @param {Base} record - An instance of Base.
     */
    remove(record) {
        this._updateIndex(record, (map, key, record, isArray = false) => {
            if (isArray) {
                map.get(key)?.delete(record.id);
            } else {
                map.delete(key);
            }
        });
    }

    _updateIndex(record, operation) {
        if (!(record instanceof Base)) {
            throw new Error("Only instances of Base are supported");
        }
        const model = record.model.name;
        this.indexes[model].forEach((index) => {
            //Accessing raw data ensures that the lazy getter is not triggered prematurely
            const indexValue = record[RAW_SYMBOL][index];
            if (!indexValue) {
                return;
            }
            const map = this.getRecordsMap(model, index);
            if (indexValue instanceof Set) {
                for (const value of indexValue) {
                    if (value) {
                        operation(map, value, record, true);
                    }
                }
            } else {
                operation(map, indexValue, record);
            }
        });
        // Returns the reactive instance
        return this.getById(model, record.id);
    }

    /**
     * Retrieves a record by model name, index key, and value.
     * @param {string} model - The name of the model.
     * @param {string} index - The name of the index
     * @param {*} value - The value to look up in the index.
     * @returns {Base| Array<Base>|undefined} - The found record or undefined if not found.
     */
    get(model, index, value) {
        const result = this.getRecordsMap(model, index).get(value);
        return result instanceof Map ? [...result.values()] : result;
    }

    /**
     * Retrieves a record by model name, id.
     * @param {string} model - The name of the model.
     * @param {*} id - The value to look up in the index.
     * @returns {Base|undefined} - The found record or undefined if not found.
     */
    getById(model, id) {
        return this.getRecordsMap(model, "id").get(id);
    }

    /**
     * Retrieves all records of a model
     * @param {string} model - The name of the model.
     * @param {Array<Base>} - Map of records by ids.
     */
    getOrderedRecords(model) {
        return Array.from(this.getRecordsMap(model, "id").values());
    }

    /**
     * Retrieves all records of a model
     * @param {string} model - The name of the model.
     * @param {string} index - The name of the index
     * @param {object} - An object where keys are IDs and values are the corresponding records
     */
    getRecordsByIds(model, index = "id") {
        const indexMap = this.getRecordsMap(model, index);
        //Check if the index is multivalued
        if (index !== "id" && indexMap.get(indexMap.keys().next().value) instanceof Map) {
            return Object.fromEntries(
                [...indexMap].map(([key, value]) => [key, Array.from(value.values())])
            );
        }
        return Object.fromEntries(indexMap);
    }

    getRecordsIds(model) {
        return Array.from(this.getRecordsMap(model, "id").keys());
    }

    /**
     * Retrieves the number of records for a given model.
     * @param {string} model - The name of the model.
     * @param {string} index - The name of the index
     * @returns {number} The total number of records.
     */
    getRecordCount(model, index = "id") {
        return this.getRecordsMap(model, index).size;
    }

    /**
     * Validates whether a given index exists for a model.
     * @param {string} model - The model name.
     * @param {string} index - The index name.
     * @returns {boolean} - True if the index exists, false otherwise.
     */
    hasIndex(model, index) {
        return this.indexes[model]?.has(index) || false;
    }

    getRecordsMap(model, index = "id") {
        const map = this.records.get(model)?.get(index);
        if (!map) {
            throw new Error(`Index '${index}' not defined for model '${model}'`);
        }
        return map;
    }
}
