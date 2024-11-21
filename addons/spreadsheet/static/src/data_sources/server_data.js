/** @odoo-module */
// @ts-check

import { EvaluationError } from "@odoo/o-spreadsheet";
import { LoadingDataError, isLoadingError } from "../o_spreadsheet/errors";

/**
 * @param {T[]} array
 * @returns {T[]}
 * @template T
 */
function removeDuplicates(array) {
    return [...new Set(array.map((el) => JSON.stringify(el)))].map((el) => JSON.parse(el));
}

export class Request {
    /**
     * @param {string} resModel
     * @param {string} method
     * @param {unknown[]} args
     */
    constructor(resModel, method, args) {
        this.resModel = resModel;
        this.method = method;
        this.args = args;
        this.key = `${resModel}/${method}(${JSON.stringify(args)})`;
    }
}

/**
 * A batch request consists of multiple requests which are combined into a single RPC.
 *
 * The batch responsibility is to combine individual requests into a single RPC payload
 * and to split the response back for individual requests.
 *
 * The server method must have the following API:
 * - The input is a list of arguments. Each list item being the arguments of a single request.
 * - The output is a list of results, ordered according to the input list
 *
 *  ```
 *  [result1, result2] = self.env['my.model'].my_batched_method([request_1_args, request_2_args])
 *  ```
 */
class ListRequestBatch {
    /**
     * @param {string} resModel
     * @param {string} method
     * @param {Request[]} requests
     */
    constructor(resModel, method, requests = []) {
        this.resModel = resModel;
        this.method = method;
        this.requests = requests;
    }

    get payload() {
        const payload = removeDuplicates(this.requests.map((request) => request.args).flat());
        return [payload];
    }

    /**
     * @param {Request} request
     */
    add(request) {
        if (request.resModel !== this.resModel || request.method !== this.method) {
            throw new Error(
                `Request ${request.resModel}/${request.method} cannot be added to the batch ${this.resModel}/${this.method}`
            );
        }
        this.requests.push(request);
    }

    /**
     * Split the batched RPC response into single request results
     *
     * @param {T[]} results
     * @returns {Map<Request, T>}
     * @template T
     */
    splitResponse(results) {
        const split = new Map();
        for (let i = 0; i < this.requests.length; i++) {
            split.set(this.requests[i], results[i]);
        }
        return split;
    }
}

export class ServerData {
    /**
     * @param {import("@web/core/orm_service").ORM} orm
     * @param {object} params
     * @param {(promise: Promise<any>) => void} [params.whenDataStartLoading]
     */
    constructor(orm, { whenDataStartLoading }) {
        /** @type {import("@web/core/orm_service").ORM} */
        this.orm = orm;
        /** @type {(promise: Promise<any>) => void} */
        this.startLoadingCallback = whenDataStartLoading ?? (() => {});
        /** @type {Record<string, unknown>}*/
        this.cache = {};
        /** @type {Record<string, Promise<unknown>>}*/
        this.asyncCache = {};
        this.batchEndpoints = {};
    }

    /**
     * @returns {{get: (resModel:string, method: string, args: unknown) => any}}
     */
    get batch() {
        return { get: (resModel, method, args) => this._getBatchItem(resModel, method, args) };
    }

    /**
     * @private
     * @param {string} resModel
     * @param {string} method
     * @param  {unknown} args
     * @returns {any}
     */
    _getBatchItem(resModel, method, args) {
        const request = new Request(resModel, method, [args]);
        if (!(request.key in this.cache)) {
            const error = new LoadingDataError();
            this.cache[request.key] = error;
            this._batch(request);
            throw error;
        }
        return this._getOrThrowCachedResponse(request);
    }

    /**
     * @param {string} resModel
     * @param {string} method
     * @param  {unknown[]} args
     * @returns {any}}
     */
    get(resModel, method, args) {
        const request = new Request(resModel, method, args);
        if (!(request.key in this.cache)) {
            const error = new LoadingDataError();
            this.cache[request.key] = error;
            const promise = this.orm
                .call(resModel, method, args)
                .then((result) => (this.cache[request.key] = result))
                .catch(
                    (error) =>
                        (this.cache[request.key] = new EvaluationError(
                            error.data?.message || error.message
                        ))
                );
            this.startLoadingCallback(promise);
            throw error;
        }
        return this._getOrThrowCachedResponse(request);
    }

    /**
     * Returns the request result if cached or the associated promise
     * @param {string} resModel
     * @param {string} method
     * @param  {unknown[]} [args]
     * @returns {Promise<any>}
     */
    async fetch(resModel, method, args) {
        const request = new Request(resModel, method, args);
        if (!(request.key in this.asyncCache)) {
            this.asyncCache[request.key] = this.orm.call(resModel, method, args);
        }
        return this.asyncCache[request.key];
    }

    /**
     * @private
     * @param {Request} request
     * @returns {void}
     */
    _batch(request) {
        const endpoint = this._getBatchEndPoint(request.resModel, request.method);
        endpoint.call(request);
    }

    /**
     * @private
     * @param {Request} request
     * @return {unknown}
     */
    _getOrThrowCachedResponse(request) {
        const data = this.cache[request.key];
        if (data instanceof Error || isLoadingError({ value: data })) {
            throw data;
        }
        return data;
    }

    /**
     * @private
     * @param {string} resModel
     * @param {string} method
     */
    _getBatchEndPoint(resModel, method) {
        if (!this.batchEndpoints[resModel] || !this.batchEndpoints[resModel][method]) {
            this.batchEndpoints[resModel] = {
                ...this.batchEndpoints[resModel],
                [method]: this._createBatchEndpoint(resModel, method),
            };
        }
        return this.batchEndpoints[resModel][method];
    }

    /**
     * @private
     * @param {string} resModel
     * @param {string} method
     */
    _createBatchEndpoint(resModel, method) {
        return new BatchEndpoint(this.orm, resModel, method, {
            whenDataStartLoading: (promise) => this.startLoadingCallback(promise),
            successCallback: (request, result) => {
                this.cache[request.key] = result;
            },
            failureCallback: (request, error) =>
                (this.cache[request.key] = new EvaluationError(
                    error.data?.message || error.message
                )),
        });
    }
}

/**
 * Collect multiple requests into a single batch.
 */
export class BatchEndpoint {
    /**
     * @param {object} orm
     * @param {string} resModel
     * @param {string} method
     * @param {object} callbacks
     * @param {function} callbacks.successCallback
     * @param {function} callbacks.failureCallback
     * @param {(promise: Promise<any>) => void} callbacks.whenDataStartLoading
     */
    constructor(orm, resModel, method, { successCallback, failureCallback, whenDataStartLoading }) {
        this.orm = orm;
        this.resModel = resModel;
        this.method = method;
        this.successCallback = successCallback;
        this.failureCallback = failureCallback;
        this.batchStartsLoadingCallback = whenDataStartLoading;

        this._isScheduled = false;
        this._pendingBatch = new ListRequestBatch(resModel, method);
    }

    /**
     * @param {Request} request
     */
    call(request) {
        this._pendingBatch.add(request);
        this._scheduleNextBatch();
    }

    /**
     * @param {Map} batchResult
     * @private
     */
    _notifyResults(batchResult) {
        for (const [request, result] of batchResult) {
            if (result instanceof Error) {
                this.failureCallback(request, result);
            } else {
                this.successCallback(request, result);
            }
        }
    }

    /**
     * @private
     */
    _scheduleNextBatch() {
        if (this._isScheduled || this._pendingBatch.requests.length === 0) {
            return;
        }
        this._isScheduled = true;
        queueMicrotask(async () => {
            this._isScheduled = false;
            const batch = this._pendingBatch;
            const { resModel, method } = batch;
            this._pendingBatch = new ListRequestBatch(resModel, method);
            const promise = this.orm
                .call(resModel, method, batch.payload)
                .then((result) => batch.splitResponse(result))
                .catch(() => this._retryOneByOne(batch))
                .then((batchResults) => this._notifyResults(batchResults));
            this.batchStartsLoadingCallback(promise);
        });
    }

    /**
     * @private
     * @param {ListRequestBatch} batch
     * @returns {Promise<Map<Request, unknown>>}
     */
    async _retryOneByOne(batch) {
        const mergedResults = new Map();
        const { resModel, method } = batch;
        const singleRequestBatches = batch.requests.map(
            (request) => new ListRequestBatch(resModel, method, [request])
        );
        const proms = [];
        for (const batch of singleRequestBatches) {
            const request = batch.requests[0];
            const prom = this.orm
                .call(resModel, method, batch.payload)
                .then((result) =>
                    mergedResults.set(request, batch.splitResponse(result).get(request))
                )
                .catch((error) => mergedResults.set(request, error));
            proms.push(prom);
        }
        await Promise.allSettled(proms);
        return mergedResults;
    }
}
