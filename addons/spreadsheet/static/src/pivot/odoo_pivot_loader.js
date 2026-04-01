//@ts-check

import { EvaluationError, CellErrorType } from "@odoo/o-spreadsheet";
import { RPCError } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import {
    getFields,
    LOADING_ERROR,
    ModelNotFoundError,
} from "@spreadsheet/data_sources/data_source";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 * @typedef {import("@spreadsheet/data_sources/odoo_data_provider").OdooDataProvider} OdooDataProvider
 */

export class OdooPivotLoader {
    /**
     * @param {OdooDataProvider} odooDataProvider
     * @param {Function} load Function to fetch data
     */
    constructor(odooDataProvider, load) {
        /** @private @type {OdooDataProvider} */
        this.odooDataProvider = odooDataProvider;
        /** @protected */
        this.loadFn = load;

        /**
         * Last time that this dataSource has been updated
         */
        this.lastUpdate = undefined;

        /** @protected */
        this.concurrency = new KeepLast();
        /** @protected */
        this.loadPromise = undefined;
        /** @protected */
        this.isFullyLoaded = false;
        /** @protected */
        this._isValid = true;
        /** @protected */
        this.loadError = undefined;
        /** @protected */
        this._isModelValid = true;
    }

    /**
     * Load data in the model
     * @param {object} [options] options for fetching data
     * @param {boolean} [options.reload=false] Force the reload of the data
     *
     * @returns {Promise} Resolved when data are fetched.
     */
    async load(options) {
        if (options && options.reload) {
            this.odooDataProvider.cancelPromise(this.loadPromise);
            this.loadPromise = undefined;
        }
        if (!this.loadPromise) {
            this.isFullyLoaded = false;
            this._isValid = true;
            this.loadError = undefined;
            this.loadPromise = this.concurrency
                .add(this.loadFn())
                .catch((e) => {
                    this._isValid = false;
                    if (e instanceof ModelNotFoundError) {
                        this._isModelValid = false;
                        this.loadError = Object.assign(
                            new EvaluationError(
                                _t(`The model "%(model)s" does not exist.`, { model: e.message })
                            ),
                            {
                                cause: e,
                            }
                        );
                        return;
                    }
                    this.loadError = Object.assign(
                        new EvaluationError(e instanceof RPCError ? e.data.message : e.message),
                        { cause: e }
                    );
                })
                .finally(() => {
                    this.lastUpdate = Date.now();
                    this.isFullyLoaded = true;
                });
            await this.odooDataProvider.notifyWhenPromiseResolves(this.loadPromise);
        }
        return this.loadPromise;
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

    isModelValid() {
        return this.isFullyLoaded && this._isModelValid;
    }

    isValid() {
        return this.isFullyLoaded && this._isValid;
    }

    hasEverBeenLoaded() {
        return this.loadPromise !== undefined;
    }

    assertIsValid({ throwOnError } = { throwOnError: true }) {
        if (!this.isFullyLoaded) {
            this.load();
            if (throwOnError) {
                throw LOADING_ERROR;
            }
            return LOADING_ERROR;
        }
        if (!this.isValid()) {
            if (throwOnError) {
                throw this.loadError;
            }
            return { value: CellErrorType.GenericError, message: this.loadError.message };
        }
    }
}
