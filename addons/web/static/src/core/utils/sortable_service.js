import { registry } from "../registry";
import { useSortable } from "@web/core/utils/sortable";
import { throttleForAnimation } from "@web/core/utils/timing";
import { reactive } from "@odoo/owl";

/**
 * @typedef SortableServiceHookParams
 * @extends SortableParams
 * @property {{el: HTMLElement} | ReturnType<typeof import("@odoo/owl").useRef>} [ref] container of sortable
 * @property {string | Symbol} [sortableId] identifier when multiple sortable on the same container
 */

const DEFAULT_SORTABLE_ID = Symbol.for("defaultSortable");
export const sortableService = {
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
                    if (sortableId in boundElement) {
                        return {
                            enable() {
                                return {
                                    cleanup: boundElement[sortableId],
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
                    if (sortableId in boundElement) {
                        delete boundElement[sortableId];
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
                        cleanupFunctions.push(() => el.removeEventListener(type, listener));
                    },
                    setup: (setupFn, dependenciesFn) => setupFunctions.set(setupFn, dependenciesFn),
                    teardown: (fn) => cleanupFunctions.push(fn),
                };

                useSortable({ setupHooks, ...hookParams });

                const boundElement = boundElements.get(element);
                if (boundElement) {
                    boundElement[sortableId] = cleanup;
                } else {
                    boundElements.set(element, { [sortableId]: cleanup });
                }

                return {
                    enable() {
                        setupFunctions.forEach((dependenciesFn, setupFn) =>
                            setupFn(...dependenciesFn())
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
