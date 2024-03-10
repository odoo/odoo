/** @odoo-module */
// @ts-check

import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { RPCError } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { EvaluationError } from "@odoo/o-spreadsheet";

/**
 * @typedef {import("./odoo_data_provider").OdooDataProvider} OdooDataProvider
 */

/**
 * DataSource is an abstract class that contains the logic of fetching and
 * maintaining access to data that have to be loaded.
 *
 * A class which extends this class have to implement the `_load` method
 * * which should load the data it needs
 *
 * Subclass can implement concrete methods to have access to a
 * particular data.
 */
export class LoadableDataSource {
    /**
     * @param {Object} param0
     * @param {OdooDataProvider} param0.odooDataProvider
     */
    constructor({ odooDataProvider }) {
        /** @protected */
        this.odooDataProvider = odooDataProvider;

        /**
         * Last time that this dataSource has been updated
         */
        this._lastUpdate = undefined;

        this._concurrency = new KeepLast();
        /**
         * Promise to control the loading of data
         */
        this._loadPromise = undefined;
        this._isFullyLoaded = false;
        this._isValid = true;
        /** @type {string} */
        this.loadingErrorMessage = "";
    }

    get _orm() {
        return this.odooDataProvider.orm;
    }

    get metadataRepository() {
        return this.odooDataProvider.metadataRepository;
    }

    get serverData() {
        return this.odooDataProvider.serverData;
    }

    /**
     * Load data in the model
     * @param {object} [params] Params for fetching data
     * @param {boolean} [params.reload=false] Force the reload of the data
     *
     * @returns {Promise} Resolved when data are fetched.
     */
    async load(params) {
        if (params && params.reload) {
            this.odooDataProvider.cancelPromise(this._loadPromise);
            this._loadPromise = undefined;
        }
        if (!this._loadPromise) {
            this._isFullyLoaded = false;
            this._isValid = true;
            this.loadingErrorMessage = "";
            this._loadPromise = this._concurrency
                .add(this._load())
                .catch((e) => {
                    this._isValid = false;
                    this.loadingErrorMessage = e instanceof RPCError ? e.data.message : e.message;
                })
                .finally(() => {
                    this._lastUpdate = Date.now();
                    this._isFullyLoaded = true;
                });
            await this.odooDataProvider.notifyWhenPromiseResolves(this._loadPromise);
        }
        return this._loadPromise;
    }

    get lastUpdate() {
        return this._lastUpdate;
    }

    /**
     * @returns {boolean}
     */
    isReady() {
        return this._isFullyLoaded;
    }

    isLoading() {
        if (this._isFullyLoaded) {
            return false;
        }
        this.load();
        return true;
    }

    hasLoadingFailed() {
        if (this._isFullyLoaded && !this._isValid) {
            return true;
        }
        return false;
    }

    /**
     * @protected
     */
    _assertDataIsLoaded() {
        if (this.isLoading()) {
            throw LOADING_ERROR;
        }
        if (this.hasLoadingFailed()) {
            throw new EvaluationError(this.loadingErrorMessage);
        }
    }

    /**
     * Load the data in the model
     *
     * @abstract
     * @protected
     */
    async _load() {}
}

export const LOADING_ERROR = new LoadingDataError();
