// @ts-check

/** @module @web/core/utils/dnd/draggable_hook_builder_owl - OWL-lifecycle adapter for the draggable hook builder */

import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { useThrottleForAnimation } from "@web/core/utils/timing";

import { makeDraggableHook as nativeMakeDraggableHook } from "./draggable_hook_builder";

/**
 * Set of default `makeDraggableHook` setup hooks that makes use of Owl lifecycle
 * and reactivity hooks to properly set up, update and tear down the elements and
 * listeners added by the draggable hook builder.
 *
 * @see {nativeMakeDraggableHook}
 * @type {typeof nativeMakeDraggableHook}
 */
export function makeDraggableHook(params) {
    return nativeMakeDraggableHook(
        /** @type {any} */ ({
            ...params,
            setupHooks: {
                addListener: useExternalListener,
                setup: useEffect,
                teardown: onWillUnmount,
                throttle: useThrottleForAnimation,
                wrapState: reactive,
            },
        }),
    );
}
