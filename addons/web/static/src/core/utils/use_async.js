/** @odoo-module **/

import { useScope } from "@odoo/owl";

// -----------------------------------------------------------------------------
// useAsync: scope-bound async, with a per-type `toAsync` protocol
// -----------------------------------------------------------------------------
//
// `useAsync(target)` captures the current component/plugin scope once and returns
// a scope-bound version of `target`. Every async result produced through it is
// guarded: if the owning scope is destroyed while a call is in flight, the
// awaiting continuation never runs (the promise is left pending) -- so it cannot
// act on a destroyed component. For rpc/ORM the in-flight request is also
// cancelled (its AbortSignal is the scope's).
//
// HOW a target binds is customizable via a `toAsync(scope)` method, so each
// source owns its own rule (rpc/ORM also cancel the in-flight request). This
// replaces the global SERVICES_METADATA registry with co-located declarations.
//
// NOTE on the "leave pending" strategy: it matches the legacy `_protectMethod`
// (a destroyed component's continuation simply never runs) and keeps the test
// suite happy (HOOT flags UNHANDLED rejections; a pending promise raises none).
// A cleaner variant would reject with AbortError (err.name === "AbortError",
// already swallowed by error_service.js), which unwinds the awaiting frame
// instead of leaking it -- switch `dropped()` below once the test harness treats
// AbortError as benign like the app does.
//
// Owl STATUS enum: NEW=0, MOUNTED=1, CANCELLED=2, DESTROYED=3. "dead" = > MOUNTED.

const MOUNTED = 1;

export function isDead(scope) {
    return scope.status > MOUNTED;
}

// what a scope-guarded call yields once its scope is dead
function dropped() {
    return new Promise(() => {}); // never settles: the continuation never runs
}

export function makeAbortError() {
    const err = new Error("The operation was aborted: the owning scope was destroyed");
    err.name = "AbortError";
    return err;
}

/**
 * Guard `promise` with `scope`: the returned promise settles like `promise`,
 * except that if `scope` is dead when `promise` fulfills, the continuation is
 * dropped (the returned promise never settles). Being a real promise, it works
 * with await/.then/.catch/.finally/Promise.all without special handling.
 *
 * @template T
 * @param {Promise<T> | T} promise
 * @param {import("@odoo/owl").Scope} scope
 * @returns {Promise<T>}
 */
export function protect(promise, scope) {
    return Promise.resolve(promise).then((result) => (isDead(scope) ? dropped() : result));
}

/**
 * Default binding for a plain async function: guard each call's result, and keep
 * the abort/cancel passthrough some call sites rely on.
 */
export function bindFunction(scope, fn) {
    return function (...args) {
        if (isDead(scope)) {
            return dropped();
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
 *   const recs = await this.orm.searchRead(...);  // dropped if destroyed in flight
 */
export function useAsync(target) {
    return toAsync(target, useScope());
}
