import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { useThrottleForAnimation } from "./timing";
import { useSortable as nativeUseSortable } from "@web/core/utils/sortable";

/**
 * Set of default `useSortable` setup hooks that makes use of Owl lifecycle
 * and reactivity hooks to properly set up, update and tear down the elements and
 * listeners added by the draggable hook builder.
 *
 * @see {nativeUseSortable}
 * @type {typeof nativeUseSortable}
 */
export function useSortable(params) {
    return nativeUseSortable({
        ...params,
        setupHooks: {
            addListener: useExternalListener,
            setup: useEffect,
            teardown: onWillUnmount,
            throttle: useThrottleForAnimation,
            wrapState: reactive,
        },
    });
}
