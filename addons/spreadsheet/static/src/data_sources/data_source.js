/** @odoo-module */
// @ts-check

import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { RPCError } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { CellErrorType, EvaluationError } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {import("./odoo_data_provider").OdooDataProvider} OdooDataProvider
 * @typedef {import("./server_data").ServerData} ServerData
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
        this._loadError = undefined;
        this._isModelValid = true;
    }

    get _orm() {
        return this.odooDataProvider.orm;
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
            this._loadError = undefined;
            this._loadPromise = this._concurrency
                .add(this._load())
                .catch((e) => {
                    this._isValid = false;
                    if (e instanceof ModelNotFoundError) {
                        this._isModelValid = false;
                        this._loadError = Object.assign(
                            new EvaluationError(
                                _t(`The model "%(model)s" does not exist.`, { model: e.message })
                            ),
                            {
                                cause: e,
                            }
                        );
                        return;
                    }
                    this._loadError = Object.assign(
                        new EvaluationError(e instanceof RPCError ? e.data.message : e.message),
                        { cause: e }
                    );
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
        return !!this._loadPromise && !this.isReady();
    }

    isValid() {
        return this.isReady() && this._isValid;
    }

    isModelValid() {
        return this.isReady() && this._isModelValid;
    }

    assertIsValid({ throwOnError } = { throwOnError: true }) {
        if (!this._isFullyLoaded) {
            this.load();
            if (throwOnError) {
                throw LOADING_ERROR;
            }
            return LOADING_ERROR;
        }
        if (!this._isValid) {
            if (throwOnError) {
                throw this._loadError;
            }
            return { value: CellErrorType.GenericError, message: this._loadError.message };
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

export class ModelNotFoundError extends Error {}

/**
 * Perform a `fields_get` on the given model and return the fields.
 * If the model is not found, a `ModelNotFoundError` is thrown.
 *
 * @param {ServerData} serverData
 * @param {string} model
 * @returns {Promise<import("@spreadsheet").OdooFields>}
 */
export async function getFields(serverData, model) {
    try {
        const fields = await serverData.fetch(model, "fields_get");
        return fields;
    } catch (e) {
        if (e instanceof RPCError && e.code === 404) {
            throw new ModelNotFoundError(model);
        }
        throw e;
    }
}
