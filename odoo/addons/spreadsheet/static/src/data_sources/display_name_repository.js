/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { LoadingDataError } from "../o_spreadsheet/errors";

/**
 * @typedef PendingDisplayName
 * @property {"PENDING"} state
 *
 * @typedef ErrorDisplayName
 * @property {"ERROR"} state
 * @property {Error} error
 *
 * @typedef CompletedDisplayName
 * @property {"COMPLETED"} state
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
     * @param {import("@web/env").OdooEnv} env
     * @param {Object} params
     * @param {function} params.whenDataIsFetched Callback to call when the
     *  display name of a record is fetched.
     */
    constructor(env, { whenDataIsFetched }) {
        this.dataFetchedCallback = whenDataIsFetched;
        /**
         * Contains the display names of records. It's organized in the following way:
         * {
         *     "res.country": {
         *         1: {
         *              "state": "COMPLETED"
         *              "value": "Belgium",
         *     },
         * }
         */
        /** @type {Object.<string, Object.<number, DisplayNameResult>>}*/
        this._displayNames = {};
        this._blockNotification = false;
        this._nameService = env.services.name;
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
        this._nameService.addDisplayNames(model, { [id]: displayName });
        if (!this._displayNames[model]) {
            this._displayNames[model] = {};
        }
        this._displayNames[model][id] = {
            state: "COMPLETED",
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
        if (!id) {
            return "";
        }
        const displayNameResult = this._displayNames[model]?.[id];
        if (!displayNameResult) {
            // Catch the error to prevent the error from being thrown in the
            // background.
            this._fetchDisplayName(model, id);
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
     * This method is called when the display name of a record is not in the
     * cache. It fetches the display name in the background.
     *
     * @param {string} model
     * @param {number} id
     *
     * @private
     * @returns {Deferred<string>}
     */
    async _fetchDisplayName(model, id) {
        if (!this._displayNames[model]) {
            this._displayNames[model] = {};
        }
        this._displayNames[model][id] = { state: "PENDING" };
        const displayNames = await this._nameService.loadDisplayNames(model, [id]);
        if (typeof displayNames[id] === "string") {
            this._displayNames[model][id].state = "COMPLETED";
            this._displayNames[model][id].value = displayNames[id];
        } else {
            this._displayNames[model][id].state = "ERROR";
            this._displayNames[model][id].error = new Error(
                _t("Name not found. You may not have the required access rights.")
            );
        }
        if (this._blockNotification) {
            return;
        }
        this._blockNotification = true;
        await Promise.resolve();
        this._blockNotification = false;
        this.dataFetchedCallback();
    }
}
