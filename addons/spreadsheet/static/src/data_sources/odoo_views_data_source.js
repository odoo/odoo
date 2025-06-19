/** @odoo-module */

import { LoadableDataSource } from "./data_source";
import { Domain } from "@web/core/domain";
import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { omit } from "@web/core/utils/objects";

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 */

/**
 * @typedef {Object} OdooModelMetaData
 * @property {string} resModel
 * @property {Array<Object>|undefined} fields
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
        this._metaData = JSON.parse(JSON.stringify(params.metaData));
        /** @protected */
        this._initialSearchParams = JSON.parse(JSON.stringify(params.searchParams));
        this._initialSearchParams.context = omit(
            this._initialSearchParams.context || {},
            ...Object.keys(this._orm.user.context)
        );
        /** @private */
        this._customDomain = this._initialSearchParams.domain;
    }

    /**
     * @protected
     */
    get _searchParams() {
        return {
            ...this._initialSearchParams,
            domain: this._customDomain,
        };
    }

    async loadMetadata() {
        if (!this._metaData.fields) {
            this._metaData.fields = await this._metadataRepository.fieldsGet(
                this._metaData.resModel
            );
        }
    }

    /**
     * @returns {Record<string, Field>} List of fields
     */
    getFields() {
        if (this._metaData.fields === undefined) {
            this.loadMetadata();
            throw new LoadingDataError();
        }
        return this._metaData.fields;
    }

    /**
     * @param {string} field Field name
     * @returns {Field | undefined} Field
     */
    getField(field) {
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

    _assertMetadataIsLoaded() {
        if (this._metaData.fields === undefined) {
            this.loadMetadata();
            throw new LoadingDataError();
        }
    }

    /**
     * Get the computed domain of this source
     * @returns {Array}
     */
    getComputedDomain() {
        return this._customDomain;
    }

    addDomain(domain) {
        const newDomain = Domain.and([this._initialSearchParams.domain, domain]);
        if (newDomain.toString() === new Domain(this._customDomain).toString()) {
            return;
        }
        this._customDomain = newDomain.toList();
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
    getModelLabel() {
        return this._metadataRepository.modelDisplayName(this._metaData.resModel);
    }

    get source() {
        return {};
    }
}
