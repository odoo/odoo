import { useExternalListener } from "@web/owl2/utils";
import { onWillUnmount, proxy, untrack, useEffect } from "@odoo/owl";
import { useThrottleForAnimation } from "./timing";
import { makeDraggableHook as nativeMakeDraggableHook } from "./draggable_hook_builder";

/**
 * Adapts the `(effect, computeDependencies)` signature expected by the native
 * draggable hook builder onto OWL3's `useEffect`. `useEffect` auto-tracks the
 * reactive values read while computing the dependencies, then (like the OWL2
 * layout effect) runs the effect untracked with those dependencies, returning
 * its cleanup.
 *
 * @param {(...deps: any[]) => (void | (() => void))} effect
 * @param {() => any[]} [computeDependencies]
 */
function setup(effect, computeDependencies = () => []) {
    useEffect(() => {
        const dependencies = computeDependencies();
        return untrack(() => effect(...dependencies));
    });
}

/**
 * Set of default `makeDraggableHook` setup hooks that makes use of Owl lifecycle
 * and reactivity hooks to properly set up, update and tear down the elements and
 * listeners added by the draggable hook builder.
 *
 * @see {nativeMakeDraggableHook}
 * @type {typeof nativeMakeDraggableHook}
 */
export function makeDraggableHook(params) {
    return nativeMakeDraggableHook({
        ...params,
        setupHooks: {
            addListener: useExternalListener,
            setup,
            teardown: onWillUnmount,
            throttle: useThrottleForAnimation,
            wrapState: proxy,
        },
    });
}
