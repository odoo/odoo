import { onWillUnmount, proxy, useListener } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";
import { makeDraggableHook as nativeMakeDraggableHook } from "./draggable_hook_builder";
import { useThrottleForAnimation } from "./timing";

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
            setup: useLayoutEffect,
            teardown: onWillUnmount,
            throttle: useThrottleForAnimation,
            wrapState: proxy,
        },
    });
}
