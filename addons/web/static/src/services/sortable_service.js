// @ts-check

/**
 * @module @web/services/sortable_service - Service for creating sortable drag-and-drop outside OWL component lifecycle
 *
 * @deprecated This service is registered but has zero consumers. All 19+ call sites
 * use the `useSortable()` OWL hook from `@web/core/utils/dnd/sortable_owl` directly.
 * Candidate for removal.
 */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useSortable } from "@web/core/utils/dnd/sortable";
import { throttleForAnimation } from "@web/core/utils/timing";

/**
 * @typedef {Record<string, any> & {
 *  ref?: {el: HTMLElement} | ReturnType<typeof import("@odoo/owl").useRef>;
 *  sortableId?: string | symbol;
 * }} SortableServiceHookParams
 */

const DEFAULT_SORTABLE_ID = Symbol.for("defaultSortable");

/**
 * Service for creating drag-and-drop sortable behaviors on DOM elements
 * outside the OWL component lifecycle. Manages element binding to avoid
 * duplicate setups and provides explicit enable/cleanup control.
 */
export const sortableService = {
    /** @returns {{ create: (hookParams: SortableServiceHookParams) => { enable: () => { cleanup: () => void } } }} */
    start() {
        /**
         * Map to avoid to setup/enable twice or more time the same element
         * @type {Map<Element, Object>}
         */
        const boundElements = new Map();
        return {
            /**
             * @param {SortableServiceHookParams} hookParams
             */
            create: (hookParams) => {
                const element = hookParams.ref.el;
                const sortableId = hookParams.sortableId ?? DEFAULT_SORTABLE_ID;
                if (boundElements.has(element)) {
                    const boundElement = boundElements.get(element);
                    if (/** @type {any} */ (sortableId) in boundElement) {
                        return {
                            enable() {
                                return {
                                    cleanup: /** @type {any} */ (boundElement)[
                                        sortableId
                                    ],
                                };
                            },
                        };
                    }
                }
                /**
                 * @type {Map<Function, function():Array>}
                 */
                const setupFunctions = new Map();
                /**
                 * @type {Array<Function>}
                 */
                const cleanupFunctions = [];

                const cleanup = () => {
                    const boundElement = boundElements.get(element);
                    if (/** @type {any} */ (sortableId) in boundElement) {
                        delete (/** @type {any} */ (boundElement)[sortableId]);
                        if (boundElement.length === 0) {
                            boundElements.delete(element);
                        }
                    }
                    cleanupFunctions.forEach((fn) => fn());
                };

                // Setup hookParam
                const setupHooks = {
                    wrapState: reactive,
                    throttle: throttleForAnimation,
                    addListener: (el, type, listener) => {
                        el.addEventListener(type, listener);
                        cleanupFunctions.push(() =>
                            el.removeEventListener(type, listener),
                        );
                    },
                    setup: (setupFn, dependenciesFn) =>
                        setupFunctions.set(setupFn, dependenciesFn),
                    teardown: (fn) => cleanupFunctions.push(fn),
                };

                useSortable(/** @type {any} */ ({ setupHooks, ...hookParams }));

                const boundElement = boundElements.get(element);
                if (boundElement) {
                    /** @type {any} */ (boundElement)[sortableId] = cleanup;
                } else {
                    boundElements.set(
                        element,
                        /** @type {any} */ ({ [sortableId]: cleanup }),
                    );
                }

                return {
                    enable() {
                        setupFunctions.forEach((dependenciesFn, setupFn) =>
                            setupFn(...dependenciesFn()),
                        );
                        return {
                            cleanup,
                        };
                    },
                };
            },
        };
    },
};

registry.category("services").add("sortable", sortableService);
