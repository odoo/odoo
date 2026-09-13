// @ts-check
/** @odoo-module native */

import { EventBus } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { RpcEvent } from "@web/core/events";
import { getKey, stableStringify } from "@web/core/network/rpc_dedup";
import { rpcLog } from "@web/core/utils/asset_log";
import { isObject, omit } from "@web/core/utils/collections/objects";
import { globalSingleton } from "@web/core/utils/global_singleton";
import { LruCache } from "@web/core/utils/lru_cache";

/** @import { RPCCache } from "@web/core/network/rpc_cache" */

/**
 * @typedef {{
 * code: number;
 * message: string;
 * data?: RPCErrorData;
 * type?: string;
 * }} JsonRpcError
 */

/**
 * @typedef {{
 * name?: string;
 * message?: string;
 * arguments?: unknown[];
 * context?: Record<string, unknown>;
 * debug?: string;
 * [extra: string]: unknown;
 * }} RPCErrorData
 */

/**
 * @typedef {{
 * cache?: boolean | { type?: "ram" | "disk"; update?: "once" | "always"; immutable?: boolean; callback?: Function };
 * silent?: boolean;
 * headers?: HeadersInit;
 * timeout?: number;
 * retry?: number | Partial<RetryConfig>;
 * dedup?: boolean;
 * signal?: AbortSignal;
 * }} RpcSettings
 */

/**
 * @typedef {{
 * data: { id: number; jsonrpc: "2.0"; method: "call"; params: Record<string, any> };
 * url: string;
 * settings?: RpcSettings;
 * result?: any;
 * error?: NetworkError;
 * }} RpcEventDetail
 */

/**
 * @template T
 * @typedef {Promise<T> & { abort: (rejectError?: boolean) => void }} RpcPromise
 */

/**
 * @typedef {{
 * subscribers: number;
 * lastOut: () => void;
 * }} InflightEntry
 */

/**
 * @typedef {{
 * rpcBus: EventBus,
 * inflightDedup: Map<string, InflightEntry & { shared: any }>,
 * inflightCacheJoin: Map<string, InflightEntry>,
 * rpcCache: RPCCache | null | undefined,
 * busListenersAttached: boolean,
 * rpcId: number,
 * dedupCallbackSeq: number,
 * headerCacheScopes: LruCache<number>,
 * headerCacheSeq: number,
 * }} RpcState
 */

const log = makeLogger("web.rpc");

/** @type {RpcState} */
const _rpcState = globalSingleton(
    "rpc",
    () =>
        /** @type {RpcState} */ ({
            rpcBus: new EventBus(),
            inflightDedup: new Map(),
            inflightCacheJoin: new Map(),
            rpcCache: undefined,
            busListenersAttached: false,
            rpcId: 0,
            dedupCallbackSeq: 0,
            headerCacheScopes: new LruCache(128),
            headerCacheSeq: 0,
        }),
);

export const rpcBus = _rpcState.rpcBus;

const RPC_SETTINGS = new Set([
    "cache",
    "silent",
    "headers",
    "timeout",
    "retry",
    "dedup",
    "signal",
]);
/** @param {{[key: string]: any}} settings */
function checkRPCSettings(settings) {
    const invalidKeys = Object.keys(settings).filter((key) => !RPC_SETTINGS.has(key));
    if (invalidKeys.length) {
        const invalid = invalidKeys.map((k) => `"${k}"`).join(", ");
        const valid = [...RPC_SETTINGS].map((k) => `"${k}"`).join(", ");
        throw new Error(
            `Invalid RPC setting(s): ${invalid}. Valid settings are: ${valid}`,
        );
    }
}

/**
 * @template {Promise<any>} T
 * @param {T} promise
 * @param {AbortSignal | undefined} signal
 * @returns {T}
 */
function attachCallerSignal(promise, signal) {
    if (!signal) {
        return promise;
    }
    const abort = () => {
        release();
        /** @type {any} */ (promise).abort?.(true);
    };
    const release = () => signal.removeEventListener("abort", abort);
    if (signal.aborted) {
        abort();
        return promise;
    }
    signal.addEventListener("abort", abort, { once: true });
    promise.then(release, release);
    return promise;
}

export class NetworkError extends Error {
    retryable = false;
}

export class RPCError extends NetworkError {
    constructor(/** @type {any[]} */ ...args) {
        super(...args);
        /** @type {string} */
        this.name = "RPC_ERROR";
        /** @type {string | null} */
        this.type = "server";
        /** @type {number | null} */
        this.code = null;
        /** @type {RPCErrorData | null} */
        this.data = null;
        /** @type {string | null} */
        this.exceptionName = null;
        /** @type {string | null} */
        this.subType = null;
        /** @type {string | undefined} */
        this.model = undefined;
    }
}

export class ConnectionLostError extends NetworkError {
    retryable = true;

    /**
     * @param {string} [url]
     * @param {...any} args
     */
    constructor(url, ...args) {
        const message = url
            ? `Connection to "${url}" couldn't be established or was interrupted`
            : "Connection couldn't be established or was interrupted";
        super(message, ...args);
        this.name = "ConnectionLostError";
        /** @type {string | undefined} */
        this.url = url;
    }
}

export class ServerOverloadError extends ConnectionLostError {
    /**
     * @param {string} url
     * @param {number} status
     * @param {...any} args
     */
    constructor(url, status, ...args) {
        super(url, ...args);
        this.name = "ServerOverloadError";
        /** @type {number} */
        this.status = status;
        this.message = url
            ? `Server returned a non-JSON response (HTTP ${status}) at "${url}"`
            : `Server returned a non-JSON response (HTTP ${status})`;
    }
}

export class InvalidResponseError extends NetworkError {
    /**
     * @param {string} url
     * @param {number} status
     * @param {...any} args
     */
    constructor(url, status, ...args) {
        const message = url
            ? `Server returned an invalid (non JSON-RPC) response (HTTP ${status}) at "${url}"`
            : `Server returned an invalid (non JSON-RPC) response (HTTP ${status})`;
        super(message, ...args);
        this.name = "InvalidResponseError";
        /** @type {number} */
        this.status = status;
        /** @type {string | undefined} */
        this.url = url;
    }
}

export class ConnectionAbortedError extends NetworkError {
    name = "ConnectionAbortedError";
}

export class RequestEntityTooLargeError extends NetworkError {
    constructor() {
        super(
            "The request you sent exceeded the maximum size limit configured on the server",
        );
        this.name = "RequestEntityTooLargeError";
    }
}

export class ConnectionTimeoutError extends NetworkError {
    retryable = true;

    /**
     * @param {string} url
     * @param {number} timeoutMs
     * @param {...any} args
     */
    constructor(url, timeoutMs, ...args) {
        super(`Request to "${url}" timed out after ${timeoutMs}ms`, ...args);
        this.name = "ConnectionTimeoutError";
        /** @type {string} */
        this.url = url;
        /** @type {number} */
        this.timeoutMs = timeoutMs;
    }
}

/**
 * @param {any} err
 * @param {string} url
 * @param {{[key: string]: any}} settings
 * @param {AbortSignal | null} timeoutSignal
 * @param {Response} [response]
 * @returns {Error}
 */
function classifyTransportFailure(err, url, settings, timeoutSignal, response) {
    if (err?.name === "TimeoutError" || timeoutSignal?.aborted) {
        return new ConnectionTimeoutError(url, settings.timeout);
    }
    if (err?.name === "AbortError") {
        return new ConnectionAbortedError("fetch abort");
    }
    if (response && response.status < 500 && err?.name === "SyntaxError") {
        return new InvalidResponseError(url, response.status);
    }
    return new ConnectionLostError(url);
}

/**
 * @param {JsonRpcError} response
 * @returns {RPCError}
 */
export function makeErrorFromResponse(response) {
    const { code, data: errorData, message, type: subType } = response;
    const error = new RPCError();
    error.exceptionName = errorData?.name ?? null;
    error.subType = subType ?? null;
    error.data = errorData ?? null;
    error.message = message;
    error.code = code;
    return error;
}

/** @param {RPCCache} cache */
rpc.setCache = function (cache) {
    _rpcState.rpcCache = cache;
};

/** @returns {Promise<void>} */
rpc.purgeCacheStorage = function () {
    return _rpcState.rpcCache?.removeStorage() ?? Promise.resolve();
};

if (!_rpcState.busListenersAttached) {
    _rpcState.busListenersAttached = true;

    rpcBus.addEventListener(RpcEvent.CLEAR_CACHES, (event) => {
        /** @type {{ tables?: string[]; model?: string } | string | string[] | undefined} */
        const detail = /** @type {CustomEvent<any>} */ (event).detail;
        if (isObject(detail)) {
            const objDetail = /** @type {{ tables?: string[]; model?: string }} */ (
                detail
            );
            if (objDetail.model) {
                _rpcState.rpcCache?.invalidateByModel(
                    /** @type {string[]} */ (objDetail.tables),
                    objDetail.model,
                );
            } else {
                _rpcState.rpcCache?.invalidate(objDetail.tables ?? null);
            }
            return;
        }
        _rpcState.rpcCache?.invalidate(
            /** @type {string | string[] | null} */ (detail ?? null),
        );
    });

    rpcBus.addEventListener(RpcEvent.REQUEST, (event) => {
        if (!rpcLog.active()) {
            return;
        }
        const detail = /** @type {CustomEvent<RpcEventDetail>} */ (event).detail;
        const params = detail.data?.params || {};
        rpcLog("request", detail.url, params.model || "", params.method || "");
    });

    rpcBus.addEventListener(RpcEvent.RESPONSE, (event) => {
        if (!rpcLog.active()) {
            return;
        }
        const detail = /** @type {CustomEvent<RpcEventDetail>} */ (event).detail;
        const params = detail.data?.params || {};
        const target = `${params.model || ""}.${params.method || detail.url}`;
        if (detail.error) {
            rpcLog(
                "error",
                target,
                detail.error.name || "error",
                detail.error.message || "",
            );
        } else {
            rpcLog("ok", target);
        }
    });
}

/** @typedef {{ retries: number; baseMs: number; maxMs: number }} RetryConfig */

/**
 * @param {number | Partial<RetryConfig>} retry
 * @returns {RetryConfig}
 */
function normalizeRetry(retry) {
    const cfg = typeof retry === "number" ? { retries: retry } : retry;
    return {
        retries: cfg.retries ?? 3,
        baseMs: cfg.baseMs ?? 200,
        maxMs: cfg.maxMs ?? 2000,
    };
}

const SERVER_OVERLOAD_BACKOFF_FLOOR_MS = 1000;

/**
 * @param {number} attempt
 * @param {RetryConfig} config
 * @param {unknown} [lastError]
 * @returns {number}
 */
function backoffDelay(attempt, config, lastError) {
    const exp = config.baseMs * 2 ** (attempt - 1);
    const jitter = Math.random() * config.baseMs;
    const capped = Math.min(exp + jitter, config.maxMs);
    if (lastError instanceof ServerOverloadError) {
        return Math.max(capped, SERVER_OVERLOAD_BACKOFF_FLOOR_MS);
    }
    return capped;
}

/**
 * @param {unknown} err
 * @returns {boolean}
 */
function isRetryable(err) {
    return err instanceof NetworkError && err.retryable === true;
}

/** @type {Map<string, InflightEntry & { shared: any }>} */
const inflightDedup = _rpcState.inflightDedup;

/** @type {Map<string, InflightEntry>} */
const inflightCacheJoin = _rpcState.inflightCacheJoin;

/**
 * @param {InflightEntry} entry
 * @param {Promise<any>} follow
 * @param {string} url
 * @param {() => void} [onDetach]
 * @returns {RpcPromise<any>}
 */
function joinInflight(entry, follow, url, onDetach) {
    entry.subscribers++;
    let detached = false;
    const { promise, resolve, reject } = Promise.withResolvers();
    follow.then(
        (/** @type {any} */ result) => {
            if (!detached) {
                resolve(result);
            }
        },
        (/** @type {any} */ error) => {
            if (!detached) {
                reject(error);
            }
        },
    );
    /** @type {any} */ (promise).abort = function (rejectError = true) {
        if (detached) {
            return;
        }
        detached = true;
        onDetach?.();
        if (--entry.subscribers === 0) {
            entry.lastOut();
        }
        if (rejectError) {
            reject(new ConnectionAbortedError(url));
        }
    };
    return /** @type {RpcPromise<any>} */ (promise);
}

/**
 * @param {{[key: string]: any}} settings
 * @returns {string}
 */
function dedupSettingsFingerprint(settings) {
    const parts = [];
    for (const key of [...RPC_SETTINGS].sort()) {
        if (key === "dedup" || key === "signal" || settings[key] === undefined) {
            continue;
        }
        let value = settings[key];
        if (key === "headers") {
            value = [...makeRequestHeaders(value).entries()];
        }
        parts.push(`${key}=${stableStringify(value)}`);
    }
    const cache = settings.cache;
    if (cache && typeof cache === "object" && typeof cache.callback === "function") {
        parts.push(`cb=${_rpcState.dedupCallbackSeq++}`);
    }
    return parts.join("&");
}

/** @param {HeadersInit} [headers] @returns {Headers} */
function makeRequestHeaders(headers) {
    const result = new Headers(headers || {});
    result.set("Content-Type", "application/json");
    return result;
}

/**
 * Copy the mutable option containers, preserving callback and signal identity.
 * Header values are normalized now so later coercion cannot change identity.
 * @param {{[key: string]: any}} settings
 * @returns {{[key: string]: any}}
 */
function copyRPCSettings(settings) {
    /** @type {{[key: string]: any}} */
    const copy = {};
    for (const key of RPC_SETTINGS) {
        const value = settings[key];
        if (value !== undefined) {
            copy[key] = value;
        }
    }
    if (copy.headers !== undefined) {
        copy.headers = makeRequestHeaders(copy.headers);
    }
    for (const key of ["cache", "retry"]) {
        if (copy[key] && typeof copy[key] === "object") {
            copy[key] = { ...copy[key] };
        }
    }
    return copy;
}

/** @param {HeadersInit} [headers] @returns {number | undefined} */
function headerCacheScope(headers) {
    if (!headers) {
        return;
    }
    const effective = makeRequestHeaders(headers);
    effective.delete("Content-Type"); // The transport always overrides this header.
    const entries = [...effective.entries()];
    if (!entries.length) {
        return;
    }
    const key = JSON.stringify(entries);
    let scope = _rpcState.headerCacheScopes.get(key);
    if (scope === undefined) {
        scope = ++_rpcState.headerCacheSeq;
        _rpcState.headerCacheScopes.set(key, scope);
    }
    return scope;
}

/**
 * @param {string} url
 * @param {{[key: string]: any}} [params]
 * @param {{[key: string]: any}} [settings]
 * @returns {any}
 */
export function rpc(url, params = {}, settings = {}) {
    return rpc._rpc(url, params, settings);
}
/**
 * @param {string} url
 * @param {{[key: string]: any}} params
 * @param {{[key: string]: any}} settings
 * @returns {Promise<any>}
 */
rpc._rpc = function (url, params, settings) {
    checkRPCSettings(settings);
    const capturedSettings = copyRPCSettings(settings);
    // Preserve the JSON property name passed to toJSON, including omission of
    // params itself. Cache delays and retries must never re-read caller objects.
    const serializedParams = JSON.stringify({ params });
    log.pipeline("snapshot", () => ({ url, codeUnits: serializedParams.length }));
    return dispatchRequest(url, serializedParams, capturedSettings);
};

/**
 * @param {string} url
 * @param {string} serializedParams
 * @param {{[key: string]: any}} settings
 * @returns {Promise<any>}
 */
function dispatchRequest(url, serializedParams, settings) {
    if (settings.dedup) {
        return _rpcDeduped(url, serializedParams, settings);
    }
    if (settings.cache && _rpcState.rpcCache) {
        return _rpcCached(url, serializedParams, settings, _rpcState.rpcCache);
    }
    if (settings.retry) {
        return _rpcWithRetry(url, serializedParams, settings);
    }
    return _rpcOnce(url, serializedParams, settings);
}

/**
 * @param {string} url
 * @param {string} serializedParams
 * @param {{[key: string]: any}} settings
 * @returns {Promise<any>}
 */
function _rpcDeduped(url, serializedParams, settings) {
    const { params } = JSON.parse(serializedParams);
    const key = `${getKey(url, params)}|${dedupSettingsFingerprint(settings)}`;
    let entry = inflightDedup.get(key);
    log.logic("dedup", () => ({ url, joined: Boolean(entry), key }));
    if (!entry) {
        const shared = /** @type {any} */ (
            dispatchRequest(url, serializedParams, omit(settings, "dedup", "signal"))
        );
        const created = {
            shared,
            subscribers: 0,
            lastOut: () => {
                if (inflightDedup.get(key) === created) {
                    inflightDedup.delete(key);
                }
                shared.abort?.(false);
            },
        };
        const onSettle = () => {
            if (inflightDedup.get(key) === created) {
                inflightDedup.delete(key);
            }
        };
        shared.then(onSettle, onSettle);
        inflightDedup.set(key, created);
        entry = created;
    }
    return attachCallerSignal(joinInflight(entry, entry.shared, url), settings.signal);
}

/**
 * @param {string} url
 * @param {string} serializedParams
 * @param {{[key: string]: any}} settings
 * @param {RPCCache} rpcCache
 * @returns {Promise<any>}
 */
function _rpcCached(url, serializedParams, settings, rpcCache) {
    const { params } = JSON.parse(serializedParams);
    const cacheSettings =
        typeof settings.cache === "boolean" ? {} : { ...settings.cache };
    const headerScope = headerCacheScope(settings.headers);
    if (headerScope !== undefined && cacheSettings.type === "disk") {
        // Header values can contain credentials. Keep these variants in RAM and
        // use opaque, never-reused scopes so neither disk keys nor cache logs
        // carry the headers. Evicting a scope merely makes its old entries cold.
        cacheSettings.type = "ram";
    }
    if (params?.model && cacheSettings.model === undefined) {
        cacheSettings.model = params.model;
    }
    cacheSettings.silent = settings.silent;
    let callerAborted = false;
    if (typeof cacheSettings.callback === "function") {
        const userCallback = cacheSettings.callback;
        cacheSettings.callback = (/** @type {any[]} */ ...args) => {
            if (!callerAborted) {
                userCallback(...args);
            }
        };
    }
    /** @type {((rejectError?: boolean) => void) | null} */
    let innerAbort = null;
    /** @type {Promise<any> | null} */
    let innerProm = null;
    /** @type {object | null} */
    let ownRequest = null;
    const fallback = (/** @type {object} */ request) => {
        ownRequest = request ?? null;
        const inner = /** @type {any} */ (
            dispatchRequest(url, serializedParams, omit(settings, "cache", "signal"))
        );
        innerProm = inner;
        if (typeof inner.abort === "function") {
            innerAbort = inner.abort.bind(inner);
        }
        return inner;
    };
    let issuedOwnRequest = false;
    cacheSettings.onRequestIssued = () => {
        issuedOwnRequest = true;
    };
    const cacheTable = params?.method || url;
    const cacheKey =
        getKey(url, params) +
        (headerScope === undefined ? "" : `|headers:${headerScope}`);
    const requestKey = `${cacheTable}/${cacheKey}`;
    const cacheProm = rpcCache.read(cacheTable, cacheKey, fallback, cacheSettings);
    log.logic("cache", () => ({ requestKey, issuedOwnRequest }));
    const onDetach = () => {
        callerAborted = true;
    };
    if (issuedOwnRequest) {
        const entry = {
            subscribers: 0,
            lastOut: () => {
                if (inflightCacheJoin.get(requestKey) === entry) {
                    inflightCacheJoin.delete(requestKey);
                }
                rpcCache.abortPending(cacheTable, cacheKey, ownRequest);
                innerAbort?.(false);
            },
        };
        const onSettle = () => {
            if (inflightCacheJoin.get(requestKey) === entry) {
                inflightCacheJoin.delete(requestKey);
            }
        };
        (innerProm ?? cacheProm).then(onSettle, onSettle);
        inflightCacheJoin.set(requestKey, entry);
        return attachCallerSignal(
            joinInflight(entry, cacheProm, url, onDetach),
            settings.signal,
        );
    }
    const joined = inflightCacheJoin.get(requestKey);
    if (joined) {
        return attachCallerSignal(
            joinInflight(joined, cacheProm, url, onDetach),
            settings.signal,
        );
    }
    /** @type {(reason?: any) => void} */
    let abortReject = () => {};
    const joinerProm = new Promise((resolve, reject) => {
        abortReject = reject;
        cacheProm.then(resolve, (/** @type {any} */ error) => {
            if (!callerAborted) {
                reject(error);
            }
        });
    });
    /** @type {any} */ (joinerProm).abort = function (rejectError = true) {
        callerAborted = true;
        if (rejectError) {
            abortReject(new ConnectionAbortedError(url));
        }
    };
    return attachCallerSignal(joinerProm, settings.signal);
}

/**
 * @param {string} body
 * @param {{[key: string]: any}} settings
 * @returns {{ controller: AbortController, timeoutSignal: AbortSignal | null, init: RequestInit }}
 */
function makeFetchRequest(body, settings) {
    const headers = makeRequestHeaders(settings.headers);
    const controller = new AbortController();
    /** @type {AbortSignal | null} */
    const timeoutSignal = settings.timeout
        ? AbortSignal.timeout(settings.timeout)
        : null;
    const extraSignals = [timeoutSignal, settings.signal || null].filter(Boolean);
    const signal = extraSignals.length
        ? AbortSignal.any([
              controller.signal,
              .../** @type {AbortSignal[]} */ (extraSignals),
          ])
        : controller.signal;
    return {
        controller,
        timeoutSignal,
        init: { method: "POST", headers, body, signal },
    };
}

/** @param {any} parsed @returns {boolean} */
function isValidRpcResponse(parsed) {
    if (!isObject(parsed)) {
        return false;
    }
    const hasResult = Object.hasOwn(parsed, "result");
    const hasError = Object.hasOwn(parsed, "error");
    if (hasResult === hasError) {
        return false;
    }
    return (
        hasResult ||
        (isObject(parsed.error) &&
            Number.isInteger(parsed.error.code) &&
            typeof parsed.error.message === "string")
    );
}

/**
 * @param {{ result: any, version?: any }} parsed
 * @returns {any}
 */
function stampVersion(parsed) {
    const result = parsed.result;
    if (
        parsed.version !== undefined &&
        result &&
        typeof result === "object" &&
        result.__version === undefined
    ) {
        result.__version = parsed.version;
    }
    return result;
}

/**
 * @param {string} url
 * @param {string} serializedParams
 * @param {{[key: string]: any}} settings
 * @returns {Promise<any>}
 */
function _rpcOnce(url, serializedParams, settings) {
    const envelope = {
        id: _rpcState.rpcId++,
        jsonrpc: "2.0",
        method: "call",
    };
    // Event listeners receive their own parsed data; mutating it cannot alter
    // the captured wire value or a later retry. Splice only JSON-produced text.
    const data = { ...JSON.parse(serializedParams), ...envelope };
    const { params } = data;
    const serializedEnvelope = JSON.stringify(envelope);
    const body =
        serializedParams === "{}"
            ? serializedEnvelope
            : serializedEnvelope.slice(0, -1) + "," + serializedParams.slice(1);
    const { controller, timeoutSignal, init } = makeFetchRequest(body, settings);
    let aborted = false;
    const busSettings = () => copyRPCSettings(omit(settings, "signal"));
    const { promise, resolve, reject } = Promise.withResolvers();
    let settled = false;
    const settleResolve = (/** @type {any} */ value) => {
        settled = true;
        resolve(value);
    };
    const settleReject = (/** @type {any} */ error) => {
        settled = true;
        reject(error);
    };
    const endSpan = log.perf(`${params?.model || url}.${params?.method || ""}`);
    /** @param {Error} error */
    const fail = (error) => {
        endSpan({ id: data.id, error: error.name });
        rpcBus.trigger(RpcEvent.RESPONSE, {
            data,
            url,
            settings: busSettings(),
            error,
        });
        settleReject(error);
    };
    /**
     * @param {Response} response
     * @returns {NetworkError}
     */
    const responseError = (response) =>
        response.status >= 500
            ? new ServerOverloadError(url, response.status)
            : new InvalidResponseError(url, response.status);

    rpcBus.trigger(RpcEvent.REQUEST, { data, url, settings: busSettings() });
    log.pipeline("request", () => ({
        id: data.id,
        url,
        model: params?.model,
        method: params?.method,
    }));

    /** @type {Promise<Response>} */
    let responsePromise;
    try {
        responsePromise = browser.fetch(url, init);
    } catch (error) {
        // Wrappers can throw before returning a promise. Route these through
        // the normal failure path so every emitted request has a response.
        responsePromise = Promise.reject(error);
    }
    responsePromise
        .then(async (response) => {
            if (aborted) {
                return;
            }
            if (response.status >= 502 && response.status <= 504) {
                return fail(new ServerOverloadError(url, response.status));
            }
            if (response.status === 413) {
                return fail(new RequestEntityTooLargeError());
            }
            const contentType = response.headers.get("content-type") || "";
            if (contentType && !/application\/json/i.test(contentType)) {
                return fail(responseError(response));
            }
            let parsed;
            try {
                parsed = await response.json();
            } catch (err) {
                if (aborted) {
                    return;
                }
                return fail(
                    classifyTransportFailure(
                        err,
                        url,
                        settings,
                        timeoutSignal,
                        response,
                    ),
                );
            }
            if (aborted) {
                return;
            }
            if (!isValidRpcResponse(parsed)) {
                return fail(responseError(response));
            }
            if (!parsed.error && !response.ok) {
                return fail(responseError(response));
            }
            if (!parsed.error) {
                const result = stampVersion(parsed);
                endSpan({ id: data.id, status: response.status });
                rpcBus.trigger(RpcEvent.RESPONSE, {
                    data,
                    url,
                    settings: busSettings(),
                    result,
                });
                settleResolve(result);
                return;
            }
            const error = makeErrorFromResponse(parsed.error);
            error.model = params?.model;
            fail(error);
        })
        .catch((err) => {
            if (aborted) {
                return;
            }
            fail(classifyTransportFailure(err, url, settings, timeoutSignal));
        });

    /** @type {RpcPromise<any>} */ (promise).abort = function (rejectError = true) {
        if (settled || aborted) {
            return;
        }
        aborted = true;
        controller.abort();
        endSpan({ id: data.id, aborted: true });
        const error = new ConnectionAbortedError("fetch abort");
        rpcBus.trigger(RpcEvent.RESPONSE, {
            data,
            url,
            settings: busSettings(),
            error,
        });
        if (rejectError) {
            settleReject(error);
        }
    };
    return /** @type {RpcPromise<any>} */ (promise);
}

/**
 * @param {string} url
 * @param {string} serializedParams
 * @param {{[key: string]: any}} settings
 * @returns {Promise<any>}
 */
function _rpcWithRetry(url, serializedParams, settings) {
    const config = normalizeRetry(settings.retry);
    const innerSettings = omit(settings, "retry");
    const { promise, resolve, reject } = Promise.withResolvers();
    let aborted = false;
    let settled = false;
    /** @type {RpcPromise<unknown> | null} */
    let currentInner = null;
    /** @type {ReturnType<typeof browser.setTimeout> | null} */
    let backoffTimer = null;
    let attempt = 0;

    const settleResolve = (/** @type {any} */ value) => {
        settled = true;
        resolve(value);
    };
    const settleReject = (/** @type {any} */ error) => {
        settled = true;
        reject(error);
    };

    const tryOnce = () => {
        backoffTimer = null;
        if (aborted) {
            return;
        }
        attempt++;
        /** @type {RpcPromise<unknown>} */
        let inner;
        try {
            inner = /** @type {RpcPromise<unknown>} */ (
                _rpcOnce(url, serializedParams, innerSettings)
            );
        } catch (error) {
            log.logic("retry.setup_failed", () => ({ url, attempt, error }));
            settleReject(error);
            return;
        }
        currentInner = inner;
        inner.then(
            (/** @type {unknown} */ result) => {
                currentInner = null;
                if (!aborted) {
                    settleResolve(result);
                }
            },
            (/** @type {unknown} */ err) => {
                currentInner = null;
                if (aborted) {
                    return;
                }
                if (isRetryable(err) && attempt <= config.retries) {
                    log.logic("retry", () => ({
                        url,
                        attempt,
                        retries: config.retries,
                        error: err,
                    }));
                    backoffTimer = browser.setTimeout(
                        tryOnce,
                        backoffDelay(attempt, config, err),
                    );
                } else {
                    settleReject(err);
                }
            },
        );
    };

    /** @type {RpcPromise<any>} */ (promise).abort = function (rejectError = true) {
        if (settled || aborted) {
            return;
        }
        aborted = true;
        if (backoffTimer !== null) {
            browser.clearTimeout(backoffTimer);
            backoffTimer = null;
        }
        currentInner?.abort?.(rejectError);
        currentInner = null;
        if (rejectError) {
            settleReject(new ConnectionAbortedError("retry chain aborted"));
        }
    };

    tryOnce();
    return /** @type {RpcPromise<any>} */ (promise);
}
