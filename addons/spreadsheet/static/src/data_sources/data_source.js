/** @odoo-module */

import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { RPCError } from "@web/core/network/rpc_service";
import { KeepLast } from "@web/core/utils/concurrency";

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
    constructor(services) {
        this._orm = services.orm;
        this._metadataRepository = services.metadataRepository;
        this._notify = services.notify;

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
        this._loadErrorMessage = "";
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
            this._loadPromise = undefined;
        }
        if (!this._loadPromise) {
            this._isFullyLoaded = false;
            this._isValid = true;
            this._loadErrorMessage = "";
            this._loadPromise = this._concurrency
                .add(this._load())
                .catch((e) => {
                    this._isValid = false;
                    this._loadErrorMessage = e instanceof RPCError ? e.data.message : e.message;
                })
                .finally(() => {
                    this._lastUpdate = Date.now();
                    this._isFullyLoaded = true;
                    this._notify();
                });
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

    /**
     * @protected
     */
    _assertDataIsLoaded() {
        if (!this._isFullyLoaded) {
            this.load();
            throw LOADING_ERROR;
        }
        if (!this._isValid) {
            throw new Error(this._loadErrorMessage);
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

const LOADING_ERROR = new LoadingDataError();
