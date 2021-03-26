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
