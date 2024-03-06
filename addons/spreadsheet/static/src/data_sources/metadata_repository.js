/** @odoo-module */
// @ts-check

import { LabelsRepository } from "./labels_repository";

import { EventBus } from "@odoo/owl";

/**
 * @typedef {object} Field
 * @property {string} name technical name
 * @property {string} type field type
 * @property {string} string display name
 * @property {string} [relation] related model technical name (only for relational fields)
 * @property {boolean} [searchable] true if a field can be searched in database
 */
/**
 * This class is used to provide facilities to fetch some common data. It's
 * used in the data sources to obtain the fields (fields_get) and the display
 * name of the models (display_name_for on ir.model).
 *
 * It also manages the labels of all the spreadsheet models (labels of basic
 * fields or display name of relational fields).
 *
 * All the results are cached in order to avoid useless rpc calls, basically
 * for different entities that are defined on the same model.
 *
 * Implementation note:
 * For the labels, when someone is asking for a display name which is not loaded yet,
 * the proxy returns directly (undefined) and a request to read display_name will
 * be triggered. All the requests created are batched and send, with only one
 * request per model, after a clock cycle.
 * At the end of this process, an event is triggered (labels-fetched)
 */
export class MetadataRepository extends EventBus {
    constructor() {
        super();
        this.labelsRepository = new LabelsRepository();
    }

    /**
     * Add a label to the cache
     *
     * @param {string} model
     * @param {string} field
     * @param {any} value
     * @param {string} label
     */
    registerLabel(model, field, value, label) {
        this.labelsRepository.setLabel(model, field, value, label);
    }

    /**
     * Get the label associated with the given arguments
     *
     * @param {string} model
     * @param {string} field
     * @param {any} value
     * @returns {string}
     */
    getLabel(model, field, value) {
        return this.labelsRepository.getLabel(model, field, value);
    }
}
