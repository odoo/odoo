/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { ServerData } from "../data_sources/server_data";

import { LoadingDataError } from "../o_spreadsheet/errors";

const { EventBus } = owl;

/**
 * @typedef {object} Field
 * @property {string} name technical name
 * @property {string} type field type
 * @property {string} string display name
 * @property {string} [relation] related model technical name (only for relational fields)
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
 * For the labels, when someone is asking for a label which is not loaded yet,
 * the proxy returns directly (undefined) and a request for a name_get will
 * be triggered. All the requests created are batched and send, with only one
 * request per model, after a clock cycle.
 * At the end of this process, an event is triggered (labels-fetched)
 */
export class MetadataRepository extends EventBus {
    constructor(orm) {
        super();
        this.orm = orm.silent;
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

        this.serverData = new ServerData(this.orm, {
            whenDataIsFetched: () => this.trigger("labels-fetched"),
        });
    }

    /**
     * Get the display name of the given model
     *
     * @param {string} model Technical name
     * @returns {Promise<string>} Display name of the model
     */
    async modelDisplayName(model) {
        const result = await this.serverData.fetch("ir.model", "display_name_for", [[model]]);
        return (result[0] && result[0].display_name) || "";
    }

    /**
     * Get the list of fields for the given model
     *
     * @param {string} model Technical name
     * @returns {Promise<Record<string, Field>>} List of fields (result of fields_get)
     */
    async fieldsGet(model) {
        return this.serverData.fetch(model, "fields_get");
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
        if (!this._labels[model]) {
            this._labels[model] = {};
        }
        if (!this._labels[model][field]) {
            this._labels[model][field] = {};
        }
        this._labels[model][field][value] = label;
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
        return (
            this._labels[model] && this._labels[model][field] && this._labels[model][field][value]
        );
    }

    /**
     * Get the display name associated to the given model-id
     * If the name is not yet loaded, a rpc will be triggered in the next clock
     * cycle.
     *
     * @param {string} model
     * @param {number} id
     * @returns {string}
     */
    getRecordDisplayName(model, id) {
        try {
            const result = this.serverData.batch.get(model, "name_get", id);
            return result[1];
        } catch (e) {
            if (e instanceof LoadingDataError) {
                throw e;
            }
            throw new Error(sprintf(_t("Unable to fetch the label of %s of model %s"), id, model));
        }
    }
}
