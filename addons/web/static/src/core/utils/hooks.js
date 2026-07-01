import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { useLayoutEffect, useRef } from "@web/owl2/utils";

import {
    onMounted,
    onPatched,
    onWillUnmount,
    props,
    proxy,
    t,
    toRaw,
    useEnv,
    useScope,
} from "@odoo/owl";
import { router } from "@web/core/browser/router";

/**
 * This file contains various custom hooks.
 * Their inner working is rather simple:
 * Each custom hook simply hooks itself to any number of owl lifecycle hooks.
 * You can then use them just like an owl hook in any Component
 * e.g.:
 * import { useBus } from "@web/core/utils/hooks";
 * ...
 * setup() {
 *    ...
 *    useBus(someBus, someEvent, callback)
 *    ...
 * }
 */

/**
 * @typedef {{ readonly el: HTMLElement | null; }} Ref
 */

// -----------------------------------------------------------------------------
// useAutofocus
// -----------------------------------------------------------------------------

/** Params accepted by {@link useAutofocus}. */
export const autofocusParamsType = t.object({
    mobile: t.boolean().optional(),
    ref: t.signal(t.instanceOf(HTMLElement)).optional(),
    refName: t.string().optional(),
    selectAll: t.boolean().optional(),
});

/**
 * Focus an element referenced by a t-ref="autofocus" in the active component
 * as soon as it appears in the DOM and if it was not displayed before.
 * If it is an input/textarea, set the selection at the end.
 * @param {Object} [params]
 * @param {string} [params.refName] override the ref name "autofocus"
 * @param {Ref | import("@odoo/owl").Signal<HTMLElement>} [params.ref] use this ref
 *  directly instead of looking one up by name. Accepts both a legacy `.el` ref and
 *  an Owl 3 signal ref.
 * @param {boolean} [params.selectAll] if true, will select the entire text value.
 * @param {boolean} [params.mobile] if true, will force autofocus on touch devices.
 * @returns {Ref | import("@odoo/owl").Signal<HTMLElement>} the element reference
 */
export function useAutofocus({ refName, ref, selectAll, mobile } = {}) {
    ref ||= useRef(refName || "autofocus");
    const getEl = () => ("el" in ref ? ref.el : ref());
    const uiService = useService("ui");

    // Prevent autofocus on touch devices to avoid the virtual keyboard from popping up unexpectedly
    if (!mobile && hasTouch()) {
        return ref;
    }
    // LEGACY
    if (!mobile && isMobileOS()) {
        return ref;
    }
    function isFocusable(el) {
        if (!el) {
            return;
        }
        if (!uiService.activeElement || uiService.activeElement.contains(el)) {
            return true;
        }
        const rootNode = el.getRootNode();
        return rootNode instanceof ShadowRoot && uiService.activeElement.contains(rootNode.host);
    }
    // LEGACY
    useLayoutEffect(
        (el) => {
            if (isFocusable(el)) {
                el.focus();
                if (["INPUT", "TEXTAREA"].includes(el.tagName) && el.type !== "number") {
                    el.selectionEnd = el.value.length;
                    el.selectionStart = selectAll ? 0 : el.value.length;
                }
            }
        },
        () => [getEl()]
    );
    return ref;
}

// -----------------------------------------------------------------------------
// useBus
// -----------------------------------------------------------------------------

/**
 * Ensures a bus event listener is attached and cleared the proper way.
 *
 * @param {import("@odoo/owl").EventBus} bus
 * @param {string} eventName
 * @param {EventListener} callback
 */
export function useBus(bus, eventName, callback) {
    const { component } = useScope();
    useLayoutEffect(
        () => {
            const listener = callback.bind(component);
            bus.addEventListener(eventName, listener);
            return () => bus.removeEventListener(eventName, listener);
        },
        () => []
    );
}

// -----------------------------------------------------------------------------
// useService
// -----------------------------------------------------------------------------

/**
 * @param {any} reason
 */
function handleAbortError(reason) {
    if (reason?.name === "AbortError") {
        return new Promise(() => {});
    } else {
        throw reason;
    }
}

/**
 * @template {(...args: any[]) => any} T
 * @param {import("@odoo/owl").Scope} scope
 * @param {T} fn
 * @returns {T}
 */
function protectMethod(scope, fn) {
    return function protectedMethod(...args) {
        if (scope.status > 1) {
            return useService.handleCallWhenDestroyed();
        }
        const promise = fn.call(this, ...args);
        const protectedPromise = scope.until(promise).catch(handleAbortError);
        return Object.assign(protectedPromise, promise);
    };
}

export const SERVICES_METADATA = {};

/**
 * Import a service into a component
 *
 * @template {keyof import("services").ServiceFactories} K
 * @param {K} serviceName
 * @returns {import("services").ServiceFactories[K]}
 */
export function useService(serviceName) {
    const { services } = useEnv();
    if (!(serviceName in services)) {
        throw new Error(`Service ${serviceName} is not available`);
    }
    const scope = useScope();
    const service = services[serviceName];
    if (SERVICES_METADATA[serviceName]) {
        if (typeof service === "function") {
            return protectMethod(scope, service);
        } else {
            const methods = SERVICES_METADATA[serviceName] ?? [];
            const result = Object.create(service);
            for (const method of methods) {
                result[method] = protectMethod(scope, service[method]);
            }
            return result;
        }
    }
    if (toRaw(service) !== service) {
        return proxy(service);
    }
    return service;
}

useService.handleCallWhenDestroyed = function handleCallWhenDestroyed() {
    return Promise.reject(new Error("Component is destroyed"));
};

// -----------------------------------------------------------------------------
// useSpellCheck
// -----------------------------------------------------------------------------

/**
 * To avoid elements to keep their spellcheck appearance when they are no
 * longer in focus. We only add this attribute when needed. To disable this
 * behavior, use the spellcheck attribute on the element.
 */
export function useSpellCheck({ refName } = {}) {
    const elements = [];
    const ref = useRef(refName || "spellcheck");
    function toggleSpellcheck(ev) {
        ev.target.spellcheck = document.activeElement === ev.target;
    }
    useLayoutEffect(
        (el) => {
            if (el) {
                const inputs =
                    ["INPUT", "TEXTAREA"].includes(el.nodeName) || el.isContentEditable
                        ? [el]
                        : el.querySelectorAll("input, textarea, [contenteditable=true]");
                inputs.forEach((input) => {
                    if (input.spellcheck !== false) {
                        elements.push(input);
                        input.addEventListener("focus", toggleSpellcheck);
                        input.addEventListener("blur", toggleSpellcheck);
                    }
                });
            }
            return () => {
                elements.forEach((input) => {
                    input.removeEventListener("focus", toggleSpellcheck);
                    input.removeEventListener("blur", toggleSpellcheck);
                });
            };
        },
        () => [ref.el]
    );
}

/**
 * @typedef {Function} ForwardRef
 * @property {HTMLElement | undefined} el
 */

/**
 * Use a ref that was forwarded by a child @see useForwardRefToParent
 *
 * @returns {ForwardRef} a ref that can be called to set its value to that of a
 *  child ref, but can otherwise be used as a normal ref object
 */
export function useChildRef() {
    let value;
    function ref(v) {
        value = v;
    }
    // Define `el` eagerly (rather than on the first assignment) so that the ref
    // is recognizable as a ref-like object (`"el" in ref` is always true) even
    // before it has been forwarded a child ref. The optional chaining keeps it
    // null-safe: reading `.el` before mount (or while detached) yields
    // `undefined` instead of throwing "Cannot read properties of undefined".
    Object.defineProperty(ref, "el", {
        get() {
            return value?.el;
        },
    });
    return ref;
}
/**
 * Forwards the given refName to the parent by calling the corresponding
 * ForwardRef received as prop. @see useChildRef
 *
 * @param {string} refName name of the ref to forward
 * @returns {Ref} the same ref that is forwarded to the
 *  parent
 */
export function useForwardRefToParent(refName) {
    const compProps = props();
    const ref = useRef(refName);
    if (compProps[refName]) {
        compProps[refName](ref);
    }
    return ref;
}
/**
 * Use the dialog service while also automatically closing the dialogs opened
 * by the current component when it is unmounted.
 *
 * @returns {import("@web/core/dialog/dialog_service").DialogServiceInterface}
 */
export function useOwnedDialogs() {
    const dialogService = useService("dialog");
    const cbs = [];
    onWillUnmount(() => {
        cbs.forEach((cb) => cb());
    });
    const addDialog = (...args) => {
        const close = dialogService.add(...args);
        cbs.push(close);
        return close;
    };
    return addDialog;
}
/**
 * Manages an event listener on a ref. Useful for hooks that want to manage
 * event listeners, especially more than one. Prefer using t-on directly in
 * components. If your hook only needs a single event listener, consider simply
 * returning it from the hook and letting the user attach it with t-on.
 *
 * @param {Ref} ref
 * @param {Parameters<typeof EventTarget.prototype.addEventListener>} listener
 */
export function useRefListener(ref, ...listener) {
    useLayoutEffect(
        (el) => {
            el?.addEventListener(...listener);
            return () => el?.removeEventListener(...listener);
        },
        () => [ref.el]
    );
}

/**
 * By using the back button feature the default back button behavior from the
 * app is actually overridden so it is important to keep count to restore the
 * default when no custom listener are remaining.
 */
export class BackButtonManager {
    _boundOnPopstate = this._onPopstate.bind(this);
    _cleanupPending = false;
    _listeners = new Map();
    _trapState = {
        trapState: true,
        nextState: router.current,
        skipRouteChange: true,
    };

    constructor() {
        this._performLatestBackAction = this._performLatestBackAction.bind(this);
    }

    /**
     * Enables the func listener, overriding default back button behavior.
     *
     * @param {import("@odoo/owl").Scope} scope
     * @param {function} func
     */
    addListener(scope, func) {
        if (this._listeners.has(scope)) {
            return;
        }
        this._listeners.set(scope, func);
        if (this._listeners.size === 1) {
            this._activate();
        }
    }

    /**
     * Disables the func listener, restoring the default back button behavior if
     * no other listeners are present.
     *
     * @param {import("@odoo/owl").Scope} scope
     */
    removeListener(scope) {
        if (!this._listeners.has(scope)) {
            return;
        }
        this._listeners.delete(scope);
        if (this._listeners.size === 0) {
            this._deactivate();
        }
    }

    _activate() {
        this._cleanupPending = false;
        window.addEventListener("popstate", this._boundOnPopstate);
        if (!history.state?.trapState) {
            router.skipLoad = true;
            history.pushState(this._trapState, "");
        }
    }

    _deactivate() {
        this._cleanupPending = true;
        // Defer cleanup so that if we are swapping between two components that both use
        // the hook, we don't destroy and recreate the trap history entry unnecessarily,
        // as this may lead to flickering and/or extra unwanted history entries.
        Promise.resolve().then(() => {
            if (!this._cleanupPending) {
                return;
            }
            this._cleanupPending = false;
            window.removeEventListener("popstate", this._boundOnPopstate);
            if (history.state?.trapState) {
                router.skipLoad = true;
                history.back();
            }
        });
    }

    _performLatestBackAction(...args) {
        if (!this._listeners.size) {
            return;
        }
        const fn = [...this._listeners.values()].at(-1);
        fn(...args);
    }

    _onPopstate() {
        this._performLatestBackAction();
        if (this._listeners.size > 0) {
            router.skipLoad = true;
            history.pushState(this._trapState, "");
        }
    }
}

const backButtonManager = new BackButtonManager();

/**
 * Hook to override default back button behavior.
 * @param {Function} handler - The function to run when back is pressed.
 * @param {Function} [shouldEnable] - Optional callback returning boolean.
 */
export function useBackButton(handler, shouldEnable) {
    if (!isMobileOS()) {
        return;
    }

    const register = () => backButtonManager.addListener(scope, handler);

    const unregister = () => backButtonManager.removeListener(scope);

    const updateRegistration = () => {
        const isActive = shouldEnable ? shouldEnable() : true;
        isActive ? register() : unregister();
    };

    const scope = useScope();

    onMounted(updateRegistration);
    onPatched(updateRegistration);
    onWillUnmount(unregister);
}
