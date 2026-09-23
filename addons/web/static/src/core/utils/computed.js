// @ts-check
/** @odoo-module native */

import { reactive, useState } from "@odoo/owl";

/**
 * A value derived from reactive state, recomputed only when something it read
 * changed or one of its keys did. It is OWL 2's stand-in for OWL 3's
 * `computed()`, which replaces it in the switch.
 *
 * `compute` receives `track`: wrap every reactive source it reads with it, so
 * that a change to what was read invalidates the value. `keys` returns the
 * non-reactive inputs (the record object, a prop), compared shallowly like
 * useEffect's dependencies. The component re-renders when the value is
 * invalidated, as if it had read the sources itself.
 *
 * @template T
 * @param {(track: <S extends object>(source: S) => S) => T} compute
 * @param {() => unknown[]} [keys]
 * @returns {() => T}
 */
export function useComputed(compute, keys = () => []) {
    const raw = { version: 0 };
    const subscribed = useState(raw);
    const trigger = reactive(raw);
    let dirty = true;
    let generation = 0;
    /** @type {unknown[]} */
    let lastKeys = [];
    /** @type {T} */
    let value;
    return () => {
        void subscribed.version;
        const nextKeys = keys();
        if (
            nextKeys.length !== lastKeys.length ||
            nextKeys.some((key, index) => key !== lastKeys[index])
        ) {
            lastKeys = nextKeys;
            dirty = true;
        }
        if (dirty) {
            dirty = false;
            const current = ++generation;
            const invalidate = () => {
                if (current === generation && !dirty) {
                    dirty = true;
                    trigger.version++;
                }
            };
            value = compute((/** @type {any} */ source) =>
                reactive(source, invalidate),
            );
        }
        return value;
    };
}
