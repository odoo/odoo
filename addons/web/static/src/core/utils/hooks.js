/** @odoo-module **/

import { SERVICES_METADATA } from "@web/env";

const { onMounted, onWillPatch, onPatched, onWillUnmount, useComponent } = owl.hooks;

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

// -----------------------------------------------------------------------------
// useAutofocus
// -----------------------------------------------------------------------------

/**
 * Focus a given selector as soon as it appears in the DOM and if it was not
 * displayed before. If the selected target is an input|textarea, set the selection
 * at the end.
 *
 * @param {Object} [params]
 * @param {string} [params.selector='autofocus'] default: select the first element
 *                 with an `autofocus` attribute.
 * @returns {Function} function that forces the focus on the next update if visible.
 */
export function useAutofocus(params = {}) {
    const comp = useComponent();
    // Prevent autofocus in mobile
    if (comp.env.isSmall) {
        return () => {};
    }
    const selector = params.selector || "[autofocus]";
    let forceFocusCount = 0;
    useEffect(
        function autofocus(target) {
            if (target) {
                target.focus();
                if (["INPUT", "TEXTAREA"].includes(target.tagName)) {
                    const inputEl = target;
                    inputEl.selectionStart = inputEl.selectionEnd = inputEl.value.length;
                }
            }
        },
        () => [comp.el.querySelector(selector), forceFocusCount]
    );

    return function focusOnUpdate() {
        forceFocusCount++; // force the effect to rerun on next patch
    };
}

// -----------------------------------------------------------------------------
// useBus
// -----------------------------------------------------------------------------

/**
 * Ensures a bus event listener is attached and cleared the proper way.
 *
 * @param {EventBus} bus
 * @param {string} eventName
 * @param {Callback} callback
 */
export function useBus(bus, eventName, callback) {
    const component = useComponent();
    useEffect(
        () => {
            bus.on(eventName, component, callback);
            return () => bus.off(eventName, component);
        },
        () => []
    );
}

// -----------------------------------------------------------------------------
// useEffect
// -----------------------------------------------------------------------------

const NO_OP = () => {};
/**
 * @callback Effect
 * @param {...any} dependencies the dependencies computed by computeDependencies
 * @returns {void|(()=>void)} a cleanup function that reverses the side
 *      effects of the effect callback.
 */

/**
 * This hook will run a callback when a component is mounted and patched, and
 * will run a cleanup function before patching and before unmounting the
 * the component.
 *
 * @param {Effect} effect the effect to run on component mount and/or patch
 * @param {()=>any[]} [computeDependencies=()=>[NaN]] a callback to compute
 *      dependencies that will decide if the effect needs to be cleaned up and
 *      run again. If the dependencies did not change, the effect will not run
 *      again. The default value returns an array containing only NaN because
 *      NaN !== NaN, which will cause the effect to rerun on every patch.
 */
export function useEffect(effect, computeDependencies = () => [NaN]) {
    let cleanup, dependencies;
    onMounted(() => {
        dependencies = computeDependencies();
        cleanup = effect(...dependencies) || NO_OP;
    });

    let shouldReapplyOnPatch = false;
    onWillPatch(() => {
        const newDeps = computeDependencies();
        shouldReapplyOnPatch = newDeps.some((val, i) => val !== dependencies[i]);
        if (shouldReapplyOnPatch) {
            cleanup();
            dependencies = newDeps;
        }
    });
    onPatched(() => {
        if (shouldReapplyOnPatch) {
            cleanup = effect(...dependencies) || NO_OP;
        }
    });

    onWillUnmount(() => cleanup());
}

// -----------------------------------------------------------------------------
// useService
// -----------------------------------------------------------------------------

function _protectMethod(component, caller, fn) {
    return async (...args) => {
        if (component.__owl__.status === 5 /* DESTROYED */) {
            throw new Error("Component is destroyed");
        }
        const result = await fn.call(caller, ...args);
        return component.__owl__.status === 5 ? new Promise(() => {}) : result;
    };
}

/**
 * Import a service into a component
 *
 * @param {string} serviceName
 * @returns {any}
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
            return _protectMethod(component, null, service);
        } else {
            const methods = SERVICES_METADATA[serviceName];
            const result = Object.create(service);
            for (let method of methods) {
                result[method] = _protectMethod(component, service, service[method]);
            }
            return result;
        }
    }
    return service;
}
