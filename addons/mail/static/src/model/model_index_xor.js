/** @odoo-module **/

export class ModelIndexXor {

    constructor(model) {
        this.model = model;
        this.recordsByValuesByFields = new Map();
        this.fieldNameAndValueByRecords = new Map();
    }

    addRecord(record, data) {
        const [fieldName, fieldValue] = [...this.model.__identifyingFieldNames].reduce(([fieldName, fieldValue], currentFieldName) => {
            const currentFieldValue = data[currentFieldName];
            if (currentFieldValue === undefined) {
                return [fieldName, fieldValue];
            }
            if (fieldName) {
                throw new Error(`Identifying field on ${this.model} with 'xor' identifying mode should have only one of the conditional values given in data. Currently have both "${fieldName}" and "${currentFieldName}".`);
            }
            return [currentFieldName, currentFieldValue];
        }, [undefined, undefined]);
        if (!this.recordsByValuesByFields.has(fieldName)) {
            this.recordsByValuesByFields.set(fieldName, new Map());
        }
        this.recordsByValuesByFields.get(fieldName).set(fieldValue, record);
        this.fieldNameAndValueByRecords.set(record, [fieldName, fieldValue]);
    }

    findRecord(data) {
        const [fieldName, fieldValue] = [...this.model.__identifyingFieldNames].reduce(([fieldName, fieldValue], currentFieldName) => {
            const currentFieldValue = data[currentFieldName];
            if (currentFieldValue === undefined) {
                return [fieldName, fieldValue];
            }
            if (fieldName) {
                throw new Error(`Identifying field on ${this.model} with 'xor' identifying mode should have only one of the conditional values given in data. Currently have both "${fieldName}" and "${currentFieldName}".`);
            }
            return [currentFieldName, currentFieldValue];
        }, [undefined, undefined]);
        if (!this.recordsByValuesByFields.has(fieldName)) {
            this.recordsByValuesByFields.set(fieldName, new Map());
        }
        return this.recordsByValuesByFields.get(fieldName).get(fieldValue);
    }

    removeRecord(record) {
        const [fieldName, fieldValue] = this.fieldNameAndValueByRecords.get(record);
        this.recordsByValuesByFields.get(fieldName).delete(fieldValue);
        this.fieldNameAndValueByRecords.delete(record);
    }

}
