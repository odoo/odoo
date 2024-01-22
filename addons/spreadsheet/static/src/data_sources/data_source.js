/** @odoo-module */

import { RPCError } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { ServerData } from "./server_data";
import { Loadable } from "./loadable";

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
        this.serverData = new ServerData(this._orm, {
            whenDataIsFetched: () => services.notify(),
        });
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
            this._loadPromise = this._concurrency
                .add(this._load())
                .catch(error => {
                    if (error instanceof RPCError) {
                        throw new Error(error.data.message);
                    }
                    throw error;
                })
                .finally(() => {
                    this._lastUpdate = Date.now();
                    this._isFullyLoaded = true;
                    // this._notify();
                });
        }
        const loadable = new Loadable(this._loadPromise);
        loadable.promise.finally(() => this._notify());
        return this._loadPromise;
    }

    lazyLoad() {

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
     * Load the data in the model
     *
     * @abstract
     * @protected
     */
    async _load() {}
}
