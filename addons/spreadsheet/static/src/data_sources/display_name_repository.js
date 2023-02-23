/** @odoo-module */

import { Deferred } from "@web/core/utils/concurrency";
import { LoadingDataError } from "../o_spreadsheet/errors";
import BatchEndpoint, { Request } from "./server_data";

/**
 * @typedef PendingDisplayName
 * @property {"PENDING"} state
 * @property {Deferred<string>} deferred
 *
 * @typedef ErrorDisplayName
 * @property {"ERROR"} state
 * @property {Deferred<string>} deferred
 * @property {Error} error
 *
 * @typedef CompletedDisplayName
 * @property {"COMPLETED"} state
 * @property {Deferred<string>} deferred
 * @property {string|undefined} value
 *
 * @typedef {PendingDisplayName | ErrorDisplayName | CompletedDisplayName} DisplayNameResult
 *
 * @typedef {[number, string]} BatchedNameGetRPCResult
 */

/**
 * This class is responsible for fetching the display names of records. It
 * caches the display names of records that have already been fetched.
 * It also provides a way to wait for the display name of a record to be
 * fetched.
 */
export class DisplayNameRepository {
    /**
     *
     * @param {import("@web/core/orm_service").ORM} orm
     * @param {Object} params
     * @param {function} params.whenDataIsFetched Callback to call when the
     *  display name of a record is fetched.
     */
    constructor(orm, { whenDataIsFetched }) {
        this.dataFetchedCallback = whenDataIsFetched;
        /**
         * Contains the display names of records. It's organized in the following way:
         * {
         *     "res.country": {
         *         1: {
         *              "value": "Belgium",
         *              "deferred": Deferred<"Belgium">,
         *     },
         * }
         */
        /** @type {Object.<string, Object.<number, DisplayNameResult>>}*/
        this._displayNames = {};
        this._orm = orm;
        this._endpoints = {};
    }

    /**
     * Get the display name of the given record.
     *
     * @param {string} model
     * @param {number} id
     * @returns {Promise<string>}
     */
    async getDisplayNameAsync(model, id) {
        const displayNameResult = this._displayNames[model] && this._displayNames[model][id];
        if (!displayNameResult) {
            return this._fetchDisplayName(model, id);
        }
        return displayNameResult.deferred;
    }

    /**
     * Set the display name of the given record. This will prevent the display name
     * from being fetched in the background.
     *
     * @param {string} model
     * @param {number} id
     * @param {string} displayName
     */
    setDisplayName(model, id, displayName) {
        if (!this._displayNames[model]) {
            this._displayNames[model] = {};
        }
        const deferred = new Deferred();
        deferred.resolve(displayName);
        this._displayNames[model][id] = {
            state: "COMPLETED",
            deferred,
            value: displayName,
        };
    }

    /**
     * Get the display name of the given record. If the record does not exist,
     * it will throw a LoadingDataError and fetch the display name in the background.
     *
     * @param {string} model
     * @param {number} id
     * @returns {string}
     */
    getDisplayName(model, id) {
        const displayNameResult = this._displayNames[model] && this._displayNames[model][id];
        if (!displayNameResult) {
            // Catch the error to prevent the error from being thrown in the
            // background.
            this._fetchDisplayName(model, id).catch(() => {});
            throw new LoadingDataError();
        }
        switch (displayNameResult.state) {
            case "ERROR":
                throw displayNameResult.error;
            case "COMPLETED":
                return displayNameResult.value;
            default:
                throw new LoadingDataError();
        }
    }

    /**
     * Get the batch endpoint for the given model. If it does not exist, it will
     * be created.
     *
     * @param {string} model
     * @returns {BatchEndpoint}
     */
    _getEndpoint(model) {
        if (!this._endpoints[model]) {
            this._endpoints[model] = new BatchEndpoint(this._orm, model, "name_get", {
                whenDataIsFetched: () => this.dataFetchedCallback(),
                successCallback: this._assignResult.bind(this),
                failureCallback: this._assignError.bind(this),
            });
        }
        return this._endpoints[model];
    }

    /**
     * This method is called when the display name of a record is successfully
     * fetched. It updates the cache and resolves the deferred of the record.
     *
     * @param {Request} request
     * @param {BatchedNameGetRPCResult} result
     *
     * @private
     */
    _assignResult(request, result) {
        const deferred = this._displayNames[request.resModel][request.args[0]].deferred;
        deferred.resolve(result && result[1]);
        this._displayNames[request.resModel][request.args[0]] = {
            state: "COMPLETED",
            deferred,
            value: result && result[1],
        };
    }

    /**
     * This method is called when the display name of a record could not be
     * fetched. It updates the cache and rejects the deferred of the record.
     *
     * @param {Request} request
     * @param {Error} error
     *
     * @private
     */
    _assignError(request, error) {
        const deferred = this._displayNames[request.resModel][request.args[0]].deferred;
        deferred.reject(error);
        this._displayNames[request.resModel][request.args[0]] = {
            state: "ERROR",
            deferred,
            error,
        };
    }

    /**
     * This method is called when the display name of a record is not in the
     * cache. It creates a deferred and fetches the display name in the
     * background.
     *
     * @param {string} model
     * @param {number} id
     *
     * @private
     * @returns {Deferred<string>}
     */
    async _fetchDisplayName(model, id) {
        const deferred = new Deferred();
        if (!this._displayNames[model]) {
            this._displayNames[model] = {};
        }
        this._displayNames[model][id] = {
            state: "PENDING",
            deferred,
        };
        const endpoint = this._getEndpoint(model);
        const request = new Request(model, "name_get", [id]);
        endpoint.call(request);
        return deferred;
    }
}
