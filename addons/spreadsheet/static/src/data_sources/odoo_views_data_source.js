/** @odoo-module */
// @ts-check

import { LOADING_ERROR, LoadableDataSource } from "./data_source";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { omit } from "@web/core/utils/objects";

/**
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 */

/**
 * @typedef {Object} OdooModelMetaData
 * @property {string} resModel
 * @property {OdooFields} [fields]
 *
 * @typedef {Object} OdooModelSearchParams
 * @property {Object} context
 * @property {Array<string>} domain
 */

export class OdooViewsDataSource extends LoadableDataSource {
    /**
     * @override
     * @param {Object} services
     * @param {Object} params
     * @param {OdooModelMetaData} params.metaData
     * @param {Object} params.searchParams
     */
    constructor(services, params) {
        super(services);
        /** @type {OdooModelMetaData} */
        this._metaData = JSON.parse(JSON.stringify(params.metaData));
        /** @protected */
        this._initialSearchParams = JSON.parse(JSON.stringify(params.searchParams));
        const userContext = user.context;
        this._initialSearchParams.context = omit(
            this._initialSearchParams.context || {},
            ...Object.keys(userContext)
        );
        /** @private */
        this._customDomain = this._initialSearchParams.domain;
        this._metaDataLoaded = false;
    }

    /**
     * @protected
     */
    get _searchParams() {
        return {
            ...this._initialSearchParams,
            domain: this.getComputedDomain(),
        };
    }

    async loadMetadata() {
        if (!this._metaData.fields) {
            this._metaData.fields = await this.serverData.fetch(
                this._metaData.resModel,
                "fields_get"
            );
        }
        this._metaDataLoaded = true;
    }

    /**
     * Ensure that the metadata are loaded. If not, throw an error
     */
    _assertMetaDataLoaded() {
        if (!this._metaDataLoaded) {
            this.loadMetadata();
            throw LOADING_ERROR;
        }
    }

    /**
     * @returns {OdooFields} List of fields
     */
    getFields() {
        this._assertMetaDataLoaded();
        return this._metaData.fields;
    }

    /**
     * @param {string} field Field name
     * @returns {OdooField | undefined} Field
     */
    getField(field) {
        this._assertMetaDataLoaded();
        return this._metaData.fields[field];
    }

    /**
     * @protected
     */
    async _load() {
        await this.loadMetadata();
    }

    isMetaDataLoaded() {
        return this._metaData.fields !== undefined;
    }

    /**
     * Get the computed domain of this source
     * @returns {Array}
     */
    getComputedDomain() {
        const userContext = user.context;
        return new Domain(this._customDomain).toList({
            ...this._initialSearchParams.context,
            ...userContext,
        });
    }

    /**
     * Get the current domain as a string
     * @returns { string }
     */
    getInitialDomainString() {
        return new Domain(this._initialSearchParams.domain).toString();
    }

    /**
     *
     * @param {string} domain
     */
    addDomain(domain) {
        const newDomain = Domain.and([this._initialSearchParams.domain, domain]).toString();
        if (newDomain.toString() === new Domain(this._customDomain).toString()) {
            return;
        }
        this._customDomain = newDomain;
        if (this._loadPromise === undefined) {
            // if the data source has never been loaded, there's no point
            // at reloading it now.
            return;
        }
        this.load({ reload: true });
    }

    /**
     * @returns {Promise<string>} Display name of the model
     */
    async getModelLabel() {
        const model = this._metaData.resModel;
        const result = await this.serverData.fetch("ir.model", "display_name_for", [[model]]);
        return (result[0] && result[0].display_name) || "";
    }
}
