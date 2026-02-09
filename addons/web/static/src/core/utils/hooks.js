import { useComponent, useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";

import { status, onWillUnmount, toRaw, onMounted, onPatched } from "@odoo/owl";
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

/**
 * Focus an element referenced by a t-ref="autofocus" in the active component
 * as soon as it appears in the DOM and if it was not displayed before.
 * If it is an input/textarea, set the selection at the end.
 * @param {Object} [params]
 * @param {string} [params.refName] override the ref name "autofocus"
 * @param {boolean} [params.selectAll] if true, will select the entire text value.
 * @param {boolean} [params.mobile] if true, will force autofocus on touch devices.
 * @returns {Ref} the element reference
 */
export function useAutofocus({ refName, selectAll, mobile } = {}) {
    const ref = useRef(refName || "autofocus");
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
        () => [ref.el]
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
    const component = useComponent();
    useLayoutEffect(
        () => {
            const listener = callback.bind(component);
            bus.addEventListener(eventName, listener);
            return () => bus.removeEventListener(eventName, listener);
        },
        () => []
    );
}

// In an object so that it can be patched in tests (prevent error on blocking RPCs after tests)
export const useServiceProtectMethodHandling = {
    fn() {
        return this.original();
    },
    mocked() {
        // Keep them unresolved so that no crash in test due to triggered RPCs by services
        return new Promise(() => {});
    },
    original() {
        return Promise.reject(new Error("Component is destroyed"));
    },
};

// -----------------------------------------------------------------------------
// useService
// -----------------------------------------------------------------------------
function _protectMethod(component, fn) {
    return function (...args) {
        if (status(component) === "destroyed") {
            return useServiceProtectMethodHandling.fn();
        }

        const prom = Promise.resolve(fn.call(this, ...args));
        const protectedProm = prom.then((result) =>
            status(component) === "destroyed" ? new Promise(() => {}) : result
        );
        return Object.assign(protectedProm, {
            abort: prom.abort,
            cancel: prom.cancel,
        });
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
    const component = useComponent();
    const { services } = component.env;
    if (!(serviceName in services)) {
        throw new Error(`Service ${serviceName} is not available`);
    }
    const service = services[serviceName];
    if (SERVICES_METADATA[serviceName]) {
        if (service instanceof Function) {
            return _protectMethod(component, service);
        } else {
            const methods = SERVICES_METADATA[serviceName] ?? [];
            const result = Object.create(service);
            for (const method of methods) {
                result[method] = _protectMethod(component, service[method]);
            }
            return result;
        }
    }
    if (toRaw(service) !== service) {
        return useState(service);
    }
    return service;
}

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
    let defined = false;
    let value;
    return function ref(v) {
        value = v;
        if (defined) {
            return;
        }
        Object.defineProperty(ref, "el", {
            get() {
                return value.el;
            },
        });
        defined = true;
    };
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
    const component = useComponent();
    const ref = useRef(refName);
    if (component.props[refName]) {
        component.props[refName](ref);
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
 * Error related to the registration of a listener
 */
class BackButtonListenerError extends Error {}

/**
 * By using the back button feature the default back button behavior from the
 * app is actually overridden so it is important to keep count to restore the
 * default when no custom listener are remaining.
 */
export class BackButtonManager {
    constructor() {
        this._listeners = new Map();
        this._onPopstate = this._onPopstate.bind(this);
        this._performLatestBackAction = this._performLatestBackAction.bind(this);
        this._trapState = { trapState: true, nextState: router.current, skipRouteChange: true };
        this._cleanupPending = false;
    }

    /**
     * Enables the func listener, overriding default back button behavior.
     *
     * @param {Component} listener
     * @param {function} func
     * @throws {BackButtonListenerError} if the listener has already been registered
     */
    addListener(listener, func) {
        if (this._listeners.has(listener)) {
            throw new BackButtonListenerError("This listener was already registered.");
        }
        this._listeners.set(listener, func);
        if (this._listeners.size === 1) {
            this._activate();
        }
    }

    /**
     * Disables the func listener, restoring the default back button behavior if
     * no other listeners are present.
     *
     * @param {Component} listener
     * @throws {BackButtonListenerError} if the listener has already been unregistered
     */
    removeListener(listener) {
        if (!this._listeners.has(listener)) {
            throw new BackButtonListenerError("This listener has already been unregistered.");
        }
        this._listeners.delete(listener);
        if (this._listeners.size === 0) {
            this._deactivate();
        }
    }

    _activate() {
        this._cleanupPending = false;
        window.addEventListener("popstate", this._onPopstate);
        if (!window.history.state?.trapState) {
            router.skipLoad = true;
            window.history.pushState(this._trapState, "");
        }
    }

    _deactivate() {
        this._cleanupPending = true;
        // Defer cleanup so that if we are swapping between two components that both use
        // the hook, we don't destroy and recreate the trap history entry unnecessarily,
        // as this may lead to flickering and/or extra unwanted history entries.
        Promise.resolve().then(() => {
            if (this._cleanupPending) {
                this._cleanupPending = false;
                window.removeEventListener("popstate", this._onPopstate);
                if (window.history.state?.trapState) {
                    router.skipLoad = true;
                    window.history.back();
                }
            }
        });
    }

    _performLatestBackAction() {
        const [listener, func] = [...this._listeners].pop();
        if (listener) {
            func.apply(listener, arguments);
        }
    }

    _onPopstate() {
        this._performLatestBackAction();
        if (this._listeners.size > 0) {
            router.skipLoad = true;
            window.history.pushState(this._trapState, "");
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
    const component = useComponent();
    let isRegistered = false;

    const register = () => {
        if (isRegistered) {
            return;
        }
        backButtonManager.addListener(component, handler);
        isRegistered = true;
    };

    const unregister = () => {
        if (!isRegistered) {
            return;
        }
        backButtonManager.removeListener(component);
        isRegistered = false;
    };

    const updateRegistration = () => {
        const isActive = shouldEnable ? shouldEnable() : true;
        isActive ? register() : unregister();
    };

    onMounted(updateRegistration);
    onPatched(updateRegistration);
    onWillUnmount(unregister);
}
