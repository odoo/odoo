// @ts-check

/** @module @web/core/network/rpc_dedup - Shares a single promise across identical concurrent RPC requests */

/**
 * RPC deduplication wrapper.
 *
 * When multiple components simultaneously request the same data (e.g.,
 * `orm.read("res.partner", [1])` from both a form and a sidebar), separate
 * RPCs are fired. This wrapper ensures identical in-flight requests share
 * a single RPC promise.
 *
 * This is a pure utility with no OWL or DOM dependencies.
 *
 * @see rpc.js for the integration point
 */

/**
 * Wrap an RPC function to deduplicate identical concurrent requests.
 *
 * While a request for a given (url, params) pair is in flight, subsequent
 * calls with the same signature return the same promise. Once the request
 * settles (success or failure), the entry is removed so future calls
 * trigger a fresh RPC.
 *
 * @template T
 * @param {(url: string, params: any) => Promise<T>} rpcFn - The original RPC function.
 * @returns {(url: string, params: any) => Promise<T>} A deduplicating wrapper.
 */
export function deduplicateRpc(rpcFn) {
    /** @type {Map<string, Promise<T>>} */
    const inflight = new Map();

    return function dedupRpc(url, params) {
        const key = buildKey(url, params);

        const existing = inflight.get(key);
        if (existing) {
            return existing;
        }

        const promise = rpcFn(url, params).finally(() => {
            inflight.delete(key);
        });

        inflight.set(key, promise);
        return promise;
    };
}

/**
 * Build a deduplication key from URL and params.
 *
 * Uses JSON.stringify for deterministic serialization. This is safe because
 * RPC params are plain JSON-serializable objects.
 *
 * @param {string} url
 * @param {any} params
 * @returns {string}
 */
export function buildKey(url, params) {
    return JSON.stringify({ url, params });
}
