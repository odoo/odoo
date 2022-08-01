/** @odoo-module **/

import { SERVICES_METADATA } from "@web/env";

const { onMounted, onPatched, onWillPatch, onWillUnmount, useComponent } = owl;

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
        function autofocus() {
            const target = comp.el.querySelector(selector);
            if (target) {
                target.focus();
                if (["INPUT", "TEXTAREA"].includes(target.tagName) && target.type !== 'number') {
                    const inputEl = target;
                    inputEl.selectionStart = inputEl.selectionEnd = inputEl.value.length;
                }
            }
        },
        () => [forceFocusCount]
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
// useListener
// -----------------------------------------------------------------------------

/**
 * The useListener hook offers an alternative to Owl's classical event
 * registration mechanism (with attribute 't-on-eventName' in xml).
 *
 * It is especially useful for abstract components, meant to be extended by
 * specific ones. If those abstract components need to define event handlers,
 * but don't have any template (because the template completely depends on
 * specific cases), then using the 't-on' mechanism isn't adequate, as the
 * handlers would be lost by the template override. In this case, using this
 * hook instead is more convenient.
 *
 * Usage: like all Owl hooks, this function has to be called in the
 * constructor of an Owl component:
 *
 *   useListener('click', () => { console.log('clicked'); });
 *
 * It also allows to do event delegation, by specifying a native query selector
 * as second argument. In this case, the handler is only called if the event
 * is triggered on an element matching the given selector.
 *
 *   useListener('click', 'button', () => { console.log('clicked'); });
 *
 * Note: components that alter the event's target (e.g. Portal) are not
 * expected to behave as expected with event delegation.
 *
 * @param {string} eventName the name of the event
 * @param {string} [querySelector] a JS native selector for event delegation
 * @param {function} handler the event handler (will be bound to the component)
 * @param {Object} [options] to be passed to addEventListener as options.
 *   Useful for listening in the capture phase
 */
export function useListener(eventName, querySelector, handler, options = {}) {
    if (typeof arguments[1] !== "string") {
        querySelector = null;
        handler = arguments[1];
        options = arguments[2] || {};
    }
    if (typeof handler !== "function") {
        throw new Error("The handler must be a function");
    }

    const comp = useComponent();
    let boundHandler;
    if (querySelector) {
        boundHandler = function (ev) {
            let el = ev.target;
            let target;
            while (el && !target) {
                if (el.matches(querySelector)) {
                    target = el;
                } else if (el === comp.el) {
                    el = null;
                } else {
                    el = el.parentElement;
                }
            }
            if (el) {
                handler.call(comp, ev);
            }
        };
    } else {
        boundHandler = handler.bind(comp);
    }
    useEffect(
        () => {
            comp.el.addEventListener(eventName, boundHandler, options);
            return () => {
                comp.el.removeEventListener(eventName, boundHandler, options);
            };
        },
        () => []
    );
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

/**
 * Executes "callback" when the component is being destroyed
 * @param  {Function} callback
 */
export function onDestroyed(callback) {
    const component = useComponent();
    const _destroy = component.__destroy;
    component.__destroy = (...args) => {
        _destroy.call(component, ...args);
        // callback is called after super to guarantee the component is actually destroyed
        callback();
    };
}
