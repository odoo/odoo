/** @odoo-module **/

import { useScope } from "@odoo/owl";

// -----------------------------------------------------------------------------
// useAsync: scope-bound async, with a per-type `toAsync` protocol
// -----------------------------------------------------------------------------
//
// `useAsync(target)` captures the current component/plugin scope once and returns
// a scope-bound version of `target`. Every async result produced through it is
// guarded: if the owning scope is destroyed while a call is in flight, the
// awaiting continuation is rejected with an AbortError instead of running on a
// dead component. `AbortError` (err.name === "AbortError") is already swallowed
// by error_service.js and recognized by owl's isAbortError, so it is silent.
//
// HOW a target binds is customizable via a `toAsync(scope)` method, so each
// source owns its own rule (rpc also cancels the in-flight request; ORM rebinds
// the single `this.rpc` choke point). This replaces the global SERVICES_METADATA
// registry with co-located, per-source declarations.
//
// Owl STATUS enum: NEW=0, MOUNTED=1, CANCELLED=2, DESTROYED=3. "dead" = > MOUNTED.

const MOUNTED = 1;

export function isDead(scope) {
    return scope.status > MOUNTED;
}

export function makeAbortError() {
    const err = new Error("The operation was aborted: the owning scope was destroyed");
    err.name = "AbortError";
    return err;
}

/**
 * Guard `promise` with `scope`: the returned (native) promise settles like
 * `promise`, except it rejects with an AbortError if `scope` is dead when
 * `promise` settles. Being a real promise, it works with await/.then/.catch/
 * .finally/Promise.all without any special handling.
 *
 * @template T
 * @param {Promise<T> | T} promise
 * @param {import("@odoo/owl").Scope} scope
 * @returns {Promise<T>}
 */
export function protect(promise, scope) {
    return Promise.resolve(promise).then(
        (value) => {
            if (isDead(scope)) {
                throw makeAbortError();
            }
            return value;
        },
        (error) => {
            throw isDead(scope) ? makeAbortError() : error;
        }
    );
}

/**
 * Default binding for a plain async function: guard each call's result, and
 * keep the abort/cancel passthrough some call sites rely on.
 */
export function bindFunction(scope, fn) {
    return function (...args) {
        if (isDead(scope)) {
            return Promise.reject(makeAbortError());
        }
        const real = fn.apply(this, args);
        const guarded = protect(real, scope);
        if (real) {
            if (typeof real.abort === "function") {
                guarded.abort = real.abort.bind(real);
            }
            if (typeof real.cancel === "function") {
                guarded.cancel = real.cancel.bind(real);
            }
        }
        return guarded;
    };
}

/**
 * The protocol dispatcher. `target.toAsync(scope)` customizes binding; otherwise
 * a plain function is guarded by default.
 */
export function toAsync(target, scope) {
    if (target && typeof target.toAsync === "function") {
        return target.toAsync(scope);
    }
    if (typeof target === "function") {
        return bindFunction(scope, target);
    }
    throw new Error(`useAsync: don't know how to bind a ${typeof target}`);
}

/**
 * Capture the current scope (call during setup -- a class field works, since
 * field initializers run inside the component's scope) and return the
 * scope-bound `target`.
 *
 *   rpc = useAsync(rpc);   orm = useAsync(ORM);
 *   const recs = await this.orm.searchRead(...);  // aborted if destroyed in flight
 */
export function useAsync(target) {
    return toAsync(target, useScope());
}
