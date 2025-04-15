/** @odoo-module */

/**
 * This class is responsible for keeping track of the labels of records. It
 * caches the labels of records that have already been fetched.
 * This class will not fetch the labels of records, it is the responsibility of
 * the caller to fetch the labels and insert them in this repository.
 */
export class LabelsRepository {
    constructor() {
        /**
         * Contains the labels of records. It's organized in the following way:
         * {
         *     "crm.lead": {
         *         "city": {
         *             "bruxelles": "Bruxelles",
         *         }
         *     },
         * }
         */
        this._labels = {};
    }

    /**
     * Get the label of a record.
     * @param {string} model technical name of the model
     * @param {string} field name of the field
     * @param {any} value value of the field
     *
     * @returns {string|undefined} label of the record
     */
    getLabel(model, field, value) {
        return (
            this._labels[model] && this._labels[model][field] && this._labels[model][field][value]
        );
    }

    /**
     * Set the label of a record.
     * @param {string} model
     * @param {string} field
     * @param {string|number} value
     * @param {string|undefined} label
     */
    setLabel(model, field, value, label) {
        if (!this._labels[model]) {
            this._labels[model] = {};
        }
        if (!this._labels[model][field]) {
            this._labels[model][field] = {};
        }
        this._labels[model][field][value] = label;
    }
}
