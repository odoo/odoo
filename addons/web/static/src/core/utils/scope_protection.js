/** @odoo-module **/

// =============================================================================
// PROTOTYPE: scope-based async "component protection" for Owl 3
// =============================================================================
//
// Goal: reproduce (and improve) the protection that `_protectMethod` gives
// today in `hooks.js` -- an async continuation belonging to a destroyed
// component must not run -- but expressed against an Owl 3 `Scope` so it works
// uniformly for components AND plugins, and without asking call sites to thread
// a scope everywhere.
//
// This file contains TWO mechanisms, because a key experiment (see
// scope_protection_probe.mjs) shows they are NOT equivalent:
//
//   (A) RECOMMENDED -- `protectMethod(scope, fn)` / `protect(promise, scope)`
//       Returns a *thenable* bound to the consuming scope. `await` DOES invoke a
//       thenable's `.then`, so this guards awaited calls at arbitrary depth.
//       The scope is captured once at the injection boundary (useScope() in
//       setup), so there is nothing to thread at call sites.
//
//   (B) EXPERIMENTAL -- `installThenPatch()` + `installEntrySeeding()`
//       The "monkeypatch global Promise + seed the ambient scope at Owl entry
//       points" idea. It works for explicit `.then()` chains but NATIVE `await`
//       bypasses a patched `Promise.prototype.then` entirely (proven in the
//       probe), so it silently misses most real code. Kept here only so the
//       limitation can be observed directly. Do not ship (B).
//
// Owl STATUS enum (from owl.js): NEW=0, MOUNTED=1, CANCELLED=2, DESTROYED=3.
// A scope is "dead" (cancelled or destroyed) when status > MOUNTED.
// =============================================================================

import { blockDom } from "@odoo/owl";

const MOUNTED = 1;

export const scopeProtectionConfig = {
    // "throw"   -> a dead scope rejects the continuation with an AbortError.
    //              This is what Owl itself does (scope.until) and what
    //              error_service.js already recognizes & ignores.
    // "pending" -> a dead scope leaves the promise forever pending (legacy
    //              _protectMethod behavior). Leaks the async frame; kept for
    //              A/B comparison only.
    strategy: "throw",
};

function isDead(scope) {
    return !!scope && scope.status > MOUNTED;
}

export function makeAbortError() {
    // name === "AbortError" so owl's isAbortError() and web's error_service both
    // treat it as expected and swallow it.
    const err = new Error("Aborted: the owning scope was destroyed");
    err.name = "AbortError";
    return err;
}

// -----------------------------------------------------------------------------
// (A) RECOMMENDED: protected thenable bound to a scope
// -----------------------------------------------------------------------------

/**
 * Wrap a real promise in a thenable that guards its continuation with `scope`.
 * Because it is a thenable (not a native promise), `await protect(p, scope)`
 * routes through this `.then`, unlike a patched Promise.prototype.then.
 *
 * If `scope` is dead when `real` settles:
 *   - strategy "throw":   the awaiting code throws an AbortError.
 *   - strategy "pending": the awaiting code never resumes.
 *
 * @template T
 * @param {Promise<T>} real
 * @param {import("@odoo/owl").Scope} scope
 * @returns {PromiseLike<T>}
 */
export function protect(real, scope) {
    const thenable = {
        then(onFulfilled, onRejected) {
            const settle = (isError, val) => {
                if (isDead(scope)) {
                    if (scopeProtectionConfig.strategy === "pending") {
                        return new Promise(() => {}); // never resolves
                    }
                    const err = makeAbortError();
                    // For `await`, onRejected is the internal reject capability;
                    // calling it makes the await throw. For an explicit
                    // `.then(onF)` with no onRejected, propagate as a rejection.
                    return onRejected ? onRejected(err) : Promise.reject(err);
                }
                if (isError) {
                    return onRejected ? onRejected(val) : Promise.reject(val);
                }
                return onFulfilled ? onFulfilled(val) : val;
            };
            return real.then(
                (v) => settle(false, v),
                (e) => settle(true, e)
            );
        },
        catch(onRejected) {
            return thenable.then(undefined, onRejected);
        },
        finally(cb) {
            return thenable.then(
                (v) => {
                    cb();
                    return v;
                },
                (e) => {
                    cb();
                    throw e;
                }
            );
        },
    };
    return thenable;
}

/**
 * Drop-in evolution of hooks.js `_protectMethod`, keyed on a Scope instead of a
 * Component and returning a protected thenable (so `await` is guarded too).
 *
 * The scope is captured ONCE, at the injection boundary (e.g. inside a
 * useService()-style hook that has called useScope() in setup). Every call
 * through the returned function is then guarded, at any await depth, with zero
 * work at the call site.
 *
 *   // in a hook, during setup:
 *   const scope = useScope();
 *   this.orm = protectMethod(scope, rawOrm.call.bind(rawOrm));
 *   // later, anywhere, any depth:
 *   const recs = await this.orm(...);  // throws AbortError if scope died
 *
 * A plugin's scope is app-lifetime, so status never exceeds MOUNTED and the
 * guard is a harmless no-op -- which is the correct behavior.
 *
 * @param {import("@odoo/owl").Scope} scope
 * @param {(...args: any[]) => any} fn
 */
export function protectMethod(scope, fn) {
    return function (...args) {
        // Cheap fast-path: already dead before we even start.
        if (isDead(scope)) {
            if (scopeProtectionConfig.strategy === "pending") {
                return new Promise(() => {});
            }
            return Promise.reject(makeAbortError());
        }
        const real = fn.apply(this, args);
        const guarded = protect(Promise.resolve(real), scope);
        // Preserve the abort/cancel passthrough that call sites rely on
        // (e.g. record_autocomplete.js `this.lastProm.abort(false)`).
        if (real) {
            guarded.abort = real.abort;
            guarded.cancel = real.cancel;
        }
        return guarded;
    };
}

// -----------------------------------------------------------------------------
// (B) EXPERIMENTAL: ambient scope + global then-patch  (DOES NOT catch `await`)
// -----------------------------------------------------------------------------

// The ambient scope, seeded at Owl entry points and (attempted to be)
// propagated across `.then`.
let currentScope = null;

export function getProtectionScope() {
    return currentScope;
}

/**
 * Seed `scope` as the ambient protection scope for the synchronous execution of
 * `fn`. Used both by the entry-point seeding and by the then-patch's callback
 * wrapper.
 */
export function runInScope(scope, fn) {
    const prev = currentScope;
    currentScope = scope;
    try {
        return fn();
    } finally {
        currentScope = prev;
    }
}

function guard(scope, cb) {
    return function (arg) {
        if (isDead(scope)) {
            if (scopeProtectionConfig.strategy === "pending") {
                return new Promise(() => {});
            }
            throw makeAbortError();
        }
        return runInScope(scope, () => cb(arg));
    };
}

let originalThen = null;
let originalMainEventHandler = null;

/**
 * Monkeypatch Promise.prototype.then to capture the ambient scope at
 * registration time and guard the callbacks.
 *
 * WARNING: native `await` on a native promise does NOT call this (verified in
 * the probe). This only affects explicit `.then()/.catch()/.finally()` chains.
 */
export function installThenPatch() {
    if (originalThen) {
        return;
    }
    originalThen = Promise.prototype.then;
    const orig = originalThen;
    // eslint-disable-next-line no-extend-native
    Promise.prototype.then = function (onFulfilled, onRejected) {
        const scope = currentScope;
        if (!scope) {
            return orig.call(this, onFulfilled, onRejected); // zero-overhead path
        }
        return orig.call(
            this,
            typeof onFulfilled === "function" ? guard(scope, onFulfilled) : onFulfilled,
            typeof onRejected === "function" ? guard(scope, onRejected) : onRejected
        );
    };
}

export function uninstallThenPatch() {
    if (originalThen) {
        // eslint-disable-next-line no-extend-native
        Promise.prototype.then = originalThen;
        originalThen = null;
    }
}

/**
 * Seed the ambient scope at the event-handler entry point. Owl does not push a
 * scope around template event handlers (see mainEventHandler in owl.js), so
 * without this there is no ambient scope when an RPC is fired from a click.
 */
export function installEntrySeeding() {
    if (originalMainEventHandler) {
        return;
    }
    const config = blockDom.config;
    originalMainEventHandler = config.mainEventHandler;
    const orig = originalMainEventHandler;
    config.mainEventHandler = function (data, ev, currentTarget) {
        let node = null;
        if (Array.isArray(data)) {
            // skip leading string modifiers, then ctx is at index 1
            let i = 0;
            while (typeof data[i] === "string") {
                i++;
            }
            const ctx = data[i + 1];
            node = ctx ? ctx.__owl__ : null;
        }
        if (node) {
            return runInScope(node, () => orig(data, ev, currentTarget));
        }
        return orig(data, ev, currentTarget);
    };
}

export function uninstallEntrySeeding() {
    if (originalMainEventHandler) {
        blockDom.config.mainEventHandler = originalMainEventHandler;
        originalMainEventHandler = null;
    }
    currentScope = null;
}
