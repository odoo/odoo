/** @odoo-module **/

export class RecordDeletedError extends Error {

    /**
     * @override
     * @param {string} recordLocalId local id of record that has been deleted
     * @param  {...any} args
     */
    constructor(recordLocalId, ...args) {
        super(...args);
        this.recordLocalId = recordLocalId;
        this.name = 'RecordDeletedError';
    }
}

export class InvalidFieldError extends Error {

    /**
     * @override
     * @param {Object} param0
     * @param {string} param0.error
     * @param {string} param0.fieldName
     * @param {string} param0.modelName
     * @param {string} param0.suggestion
     */
    constructor({ error, fieldName, modelName, suggestion }) {
        super();
        this._modelName = modelName;
        this._fieldName = fieldName;
        this._error = error;
        this._suggestion = suggestion;
        this.name = 'InvalidFieldError';
        this.message = `Invalid declaration of "${this._modelName}/${this._fieldName}": ${this._error} (Suggestion: ${this._suggestion})`;
    }
}
