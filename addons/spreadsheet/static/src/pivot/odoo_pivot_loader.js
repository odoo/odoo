/** @odoo-module native */
//@ts-check

import { getFields, LoadableDataSource } from "@spreadsheet/data_sources/data_source";

/**
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 * @typedef {import("@spreadsheet/data_sources/odoo_data_provider").OdooDataProvider} OdooDataProvider
 */

/**
 * Loads pivot data via an injected load function, reusing LoadableDataSource's
 * load/error/validity state machine instead of re-implementing it.
 */
export class OdooPivotLoader extends LoadableDataSource {
    /**
     * @param {OdooDataProvider} odooDataProvider
     * @param {Function} load Function to fetch data
     */
    constructor(odooDataProvider, load) {
        super({ odooDataProvider });
        /** @protected */
        this.loadFn = load;
    }

    /**
     * @protected
     */
    async _load() {
        return this.loadFn();
    }

    /**
     * @param {string} model Technical name of the model
     * @returns {Promise<OdooFields>} Fields of the model
     */
    async getFields(model) {
        return getFields(this.odooDataProvider.fieldService, model);
    }
    /**
     * @param {string} model Technical name of the model
     * @returns {Promise<string>} Display name of the model
     */
    async getModelLabel(model) {
        const result = await this.odooDataProvider.orm
            .cache({ type: "disk" })
            .call("ir.model", "display_name_for", [[model]]);
        return result[0]?.display_name || "";
    }

    hasEverBeenLoaded() {
        return this._loadPromise !== undefined;
    }
}
