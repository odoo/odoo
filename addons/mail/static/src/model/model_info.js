/** @odoo-module **/

export class ModelInfo {

    constructor({ model, identifyingMode }) {
        this.model = model;
        this.identifyingMode = identifyingMode;
        this.records = new Set();
    }

}
