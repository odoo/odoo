/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { ServerData } from "../data_sources/server_data";

import { LoadingDataError } from "../o_spreadsheet/errors";
import { DisplayNameRepository } from "./display_name_repository";
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
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    constructor(env) {
        super();
        this.orm = env.services.orm.silent;
        this.nameService = env.services.name;

        this.serverData = new ServerData(this.orm, {
            whenDataIsFetched: () => this.trigger("labels-fetched"),
        });

        this.labelsRepository = new LabelsRepository();

        this.displayNameRepository = new DisplayNameRepository(env, {
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

    /**
     * Save the result of display_name read request in the cache
     */
    setDisplayName(model, id, result) {
        this.displayNameRepository.setDisplayName(model, id, result);
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
            return this.displayNameRepository.getDisplayName(model, id);
        } catch (e) {
            if (e instanceof LoadingDataError) {
                throw e;
            }
            throw new Error(sprintf(_t("Unable to fetch the label of %s of model %s"), id, model));
        }
    }
}
