// @ts-check

/** @module @web/model/relational_model/onchange_coalescer - Debounce rapid field changes into a single coalesced onchange RPC call */

/**
 * Onchange coalescing utility for the relational model.
 *
 * When a user types rapidly in a form field, each keystroke can trigger a
 * separate onchange RPC. This utility coalesces rapid changes into a single
 * onchange call, reducing server load and improving responsiveness.
 *
 * This is a pure utility with no OWL or DOM dependencies — testable with
 * plain assertions.
 *
 * @see record.js _getOnchangeValues for the integration point
 */

/**
 * Create a coalescer that batches rapid field changes into a single evaluation.
 *
 * Usage:
 *   const coalescer = createOnchangeCoalescer(async (changes) => {
 *       return await orm.onchange(model, ids, changes, fields, spec);
 *   });
 *
 *   // These three rapid calls produce a single evaluateFn call:
 *   coalescer.queue("name", "Jo");
 *   coalescer.queue("name", "Joh");
 *   await coalescer.queue("name", "John");
 *   // evaluateFn called once with { name: "John" }
 *
 * @param {(changes: Record<string, any>) => Promise<Record<string, any>>} evaluateFn
 *     The function that performs the actual onchange RPC.
 * @param {{ delay?: number }} [options]
 * @param {number} [options.delay=200] - Debounce window in milliseconds.
 * @returns {{ queue: (fieldName: string, value: any) => Promise<Record<string, any>>, flush: () => Promise<Record<string, any>>, pending: Record<string, any> | null }}
 */
export function createOnchangeCoalescer(evaluateFn, { delay = 200 } = {}) {
    /** @type {Record<string, any> | null} */
    let pending = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    let timer = null;
    /** @type {Array<(result: Record<string, any>) => void>} */
    let resolvers = [];

    const coalescer = {
        /** Expose pending changes for inspection (e.g., in tests). */
        get pending() {
            return pending;
        },

        /**
         * Queue a field change. Returns a promise that resolves when the
         * coalesced batch is evaluated.
         *
         * @param {string} fieldName
         * @param {any} value
         * @returns {Promise<Record<string, any>>}
         */
        queue(fieldName, value) {
            if (!pending) {
                pending = {};
            }
            // Later values for the same field overwrite earlier ones
            pending[fieldName] = value;

            if (timer !== null) {
                clearTimeout(timer);
            }
            return new Promise((resolve) => {
                resolvers.push(resolve);
                timer = setTimeout(() => coalescer.flush(), delay);
            });
        },

        /**
         * Immediately evaluate all pending changes without waiting for the
         * debounce timer. Safe to call even when nothing is pending (returns {}).
         *
         * @returns {Promise<Record<string, any>>}
         */
        async flush() {
            if (!pending) {
                return {};
            }
            const changes = pending;
            const currentResolvers = resolvers;
            pending = null;
            resolvers = [];
            if (timer !== null) {
                clearTimeout(timer);
                timer = null;
            }

            const result = await evaluateFn(changes);
            for (const resolve of currentResolvers) {
                resolve(result);
            }
            return result;
        },
    };

    return coalescer;
}
