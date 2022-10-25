/** @odoo-module **/

export class RecordInfo {

    constructor({ record }) {
        this.record = record;
        /**
         * Listeners that are bound to this record, to be notified of
         * change in dependencies of compute, related and "on change".
         */
        this.listeners = [];
    }

}
