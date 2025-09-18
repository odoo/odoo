// @ts-check

/** @module @web/core/utils/dnd/sortable_owl - OWL-lifecycle adapter for useSortable with reactive state */

import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { useSortable as nativeUseSortable } from "@web/core/utils/dnd/sortable";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * Set of default `useSortable` setup hooks that makes use of Owl lifecycle
 * and reactivity hooks to properly set up, update and tear down the elements and
 * listeners added by the draggable hook builder.
 *
 * @see {nativeUseSortable}
 * @type {typeof nativeUseSortable}
 */
export function useSortable(params) {
    return nativeUseSortable(
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
