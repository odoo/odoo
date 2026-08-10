import { onMounted, onPatched, onWillUnmount, proxy, t, toRaw, untrack, useScope } from "@odoo/owl";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { router } from "@web/core/browser/router";
import { useEnv, useLayoutEffect } from "@web/owl2/utils";

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
 * @typedef {import("@odoo/owl").Signal<HTMLElement> | (() => HTMLElement | null)} Ref
 */

// -----------------------------------------------------------------------------
// useAutofocus
// -----------------------------------------------------------------------------

/** Params accepted by {@link useAutofocus}. */
export const autofocusParamsType = t.object({
    mobile: t.boolean().optional(),
    ref: t.signal(t.instanceOf(HTMLElement)).optional(),
    selectAll: t.boolean().optional(),
});

/**
 * Focus an element referenced by a t-ref="autofocus" in the active component
 * as soon as it appears in the DOM and if it was not displayed before.
 * If it is an input/textarea, set the selection at the end.
 * @param {Object} [params]
 * @param {import("@odoo/owl").Signal<HTMLElement>} [params.ref] the ref to focus
 * @param {boolean} [params.selectAll] if true, will select the entire text value.
 * @param {boolean} [params.mobile] if true, will force autofocus on touch devices.
 * @returns {import("@odoo/owl").Signal<HTMLElement> | undefined} the element reference
 */
export function useAutofocus({ ref, selectAll, mobile } = {}) {
    // The read is untracked: getEl() is called in the layout-effect deps (run
    // during the render phase), so a tracked read would subscribe the component
    // to the ref signal, and setting the ref on mount would schedule a spurious
    // re-render that can reset an input bound with t-att-value (e.g. calendar
    // quick-create title).
    const getEl = () => (ref ? untrack(ref) : undefined);
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
 * @template {EventTarget} T
 * @param {T} target
 * @param {Parameters<T["addEventListener"]>[0]} type
 * @param {Parameters<T["addEventListener"]>[1]} listener
 */
export function useBus(target, type, listener) {
    onMounted(() => target.addEventListener(type, listener));
    onWillUnmount(() => target.removeEventListener(type, listener));
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
        if (scope.status >= 2) {
            return useService.handleCallWhenDestroyed();
        }
        const promise = fn.call(this, ...args);
        const protectedPromise = scope.run(() => promise).catch(handleAbortError);
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
export function useSpellCheck({ ref } = {}) {
    const elements = [];
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
        () => [untrack(ref)]
    );
}

/**
 * Use the dialog service while also automatically closing the dialogs opened
 * by the current component when it is unmounted.
 *
 * @returns {import("@web/core/dialog/dialog_service").DialogServiceInterface}
 */
export function useOwnedDialogs(options = {}) {
    const scope = useScope();
    const dialogService = useService("dialog");
    const cbs = [];
    onWillUnmount(() => {
        cbs.forEach((cb) => cb());
    });
    const addDialog = (component, props, dialogOptions = {}) => {
        const newOptions = Object.create(dialogOptions);
        if (options.withScope) {
            newOptions.scope = scope;
        }
        const close = dialogService.add(component, props, newOptions);
        cbs.push(close);
        return close;
    };
    return addDialog;
}

/**
 * By using the back button feature the default back button behavior from the
 * app is actually overridden so it is important to keep count to restore the
 * default when no custom listener are remaining.
 */
export class BackButtonManager {
    _boundOnPopstate = this._onPopstate.bind(this);
    _boundPerformLatestBackAction = this._performLatestBackAction.bind(this);
    _cleanupPending = false;
    _listeners = new Map();
    _trapState = {
        nextState: router.current,
        skipRouteChange: true,
        trapState: true,
    };

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
