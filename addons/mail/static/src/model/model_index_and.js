/** @odoo-module **/

export class ModelIndexAnd {

    constructor(model) {
        this.model = model;
        this.recordsByValuesTree = new Map();
        this.valuesByRecords = new Map();
        this.singleton = undefined;
    }

    addRecord(record, data) {
        if (this.model.__identifyingFieldNames.size === 0) {
            this.singleton = record;
            return;
        }
        const valuesOfRecord = [];
        let res = this.recordsByValuesTree;
        const { length, [length - 1]: lastFieldName } = [...this.model.__identifyingFieldNames];
        for (const fieldName of this.model.__identifyingFieldNames) {
            const fieldValue = data[fieldName];
            if (fieldValue === undefined) {
                throw new Error(`Identifying field "${fieldName}" is lacking a value on ${this.model} with 'and' identifying mode`);
            }
            valuesOfRecord.push(fieldValue);
            if (!res.has(fieldValue)) {
                res.set(fieldValue, fieldName === lastFieldName ? record : new Map());
            }
            res = res.get(fieldValue);
        }
        this.valuesByRecords.set(record, valuesOfRecord);
    }

    findRecord(data) {
        if (this.model.__identifyingFieldNames.size === 0) {
            return this.singleton;
        }
        let res = this.recordsByValuesTree;
        for (const fieldName of this.model.__identifyingFieldNames) {
            const fieldValue = data[fieldName];
            if (fieldValue === undefined) {
                throw new Error(`Identifying field "${fieldName}" is lacking a value on ${this.model} with 'and' identifying mode`);
            }
            res = res.get(fieldValue);
            if (!res) {
                return;
            }
        }
        return res;
    }

    removeRecord(record) {
        if (this.model.__identifyingFieldNames.size === 0) {
            this.singleton = undefined;
            return;
        }
        const values = this.valuesByRecords.get(record);
        let res = this.recordsByValuesTree;
        for (let i = 0; i < values.length; i++) {
            const index = values[i];
            if (i === values.length - 1) {
                res.delete(index);
                break;
            }
            res = res.get(index);
        }
        this.valuesByRecords.delete(record);
    }

}
