/** @odoo-module **/

import { SERVICES_METADATA } from "@web/env";
import { isMobileOS } from "@web/core/browser/feature_detection";

import { status, useComponent, useEffect, useRef, onWillUnmount } from "@odoo/owl";

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
 * @param {boolean} [params.mobile] if true, will autofocus on mobile devices.
 * @returns {Ref} the element reference
 */
export function useAutofocus({ refName, selectAll, mobile } = {}) {
    const comp = useComponent();
    const ref = useRef(refName || "autofocus");
    const uiService = useService("ui");

    // Prevent autofocus in mobile
    if (!mobile && comp.env.isSmall) {
        return ref;
    }
    // LEGACY
    if (!mobile && isMobileOS()) {
        return ref;
    }
    // LEGACY
    useEffect(
        (el) => {
            if (el && (!uiService.activeElement || uiService.activeElement.contains(el))) {
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
    useEffect(
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
function _protectMethod(component, fn) {
    return function (...args) {
        if (status(component) === "destroyed") {
            return Promise.reject(new Error("Component is destroyed"));
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

/**
 * Import a service into a component
 *
 * @template {keyof import("services").Services} K
 * @param {K} serviceName
 * @returns {import("services").Services[K]}
 */
export function useService(serviceName) {
    const component = useComponent();
    const { services } = component.env;
    if (!(serviceName in services)) {
        throw new Error(`Service ${serviceName} is not available`);
    }
    const service = services[serviceName];
    if (serviceName in SERVICES_METADATA) {
        if (service instanceof Function) {
            return _protectMethod(component, service);
        } else {
            const methods = SERVICES_METADATA[serviceName];
            const result = Object.create(service);
            for (const method of methods) {
                result[method] = _protectMethod(component, service[method]);
            }
            return result;
        }
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
    useEffect(
        (el) => {
            if (el) {
                const inputs =
                    ["INPUT", "TEXTAREA"].includes(el.nodeName) || el.contenteditable
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
    useEffect(
        (el) => {
            el?.addEventListener(...listener);
            return () => el?.removeEventListener(...listener);
        },
        () => [ref.el]
    );
}
