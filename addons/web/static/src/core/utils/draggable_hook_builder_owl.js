import { onMounted, onPatched, onWillUnmount, proxy, useListener } from "@odoo/owl";
import { makeDraggableHook as nativeMakeDraggableHook } from "./draggable_hook_builder";
import { useThrottleForAnimation } from "./timing";

function setup(effect, computeDependencies = () => []) {
    let cleanup;
    let dependencies;
    onMounted(() => {
        dependencies = computeDependencies();
        cleanup = effect(...dependencies);
    });
    onPatched(() => {
        const newDependencies = computeDependencies();
        if (newDependencies.some((dep, i) => dep !== dependencies[i])) {
            dependencies = newDependencies;
            cleanup?.();
            cleanup = effect(...dependencies);
        }
    });
    onWillUnmount(() => cleanup?.());
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
            addListener: useListener,
            setup,
            teardown: onWillUnmount,
            throttle: useThrottleForAnimation,
            wrapState: proxy,
        },
    });
}
