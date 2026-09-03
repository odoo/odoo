import { registry } from "@web/core/registry";

/**
 * Notifies the changes of the elements fixed at the top of the page (e.g. the
 * header) and keeps track of the height they cover: the "top fixed offset".
 * It is measured once per change and given to the registered callbacks.
 */
export const websiteMenusService = {
    start() {
        const updateCallbacks = new Set();
        // Elements that compute the height they cover themselves (e.g. a
        // fading header), mapped to the function returning their bottom.
        const topFixedElements = new Map();
        let topFixedOffset = 0;

        const computeTopFixedOffset = () => {
            const bottoms = Array.from(topFixedElements.values(), (getBottom) => getBottom());
            for (const el of document.querySelectorAll(".o_top_fixed_element")) {
                if (!topFixedElements.has(el)) {
                    bottoms.push(el.getBoundingClientRect().bottom);
                }
            }
            return Math.max(0, ...bottoms);
        };

        return {
            updateCallbacks,
            /**
             * @param {Function} fn called with the top fixed offset each time
             *      the top fixed elements change
             * @returns {Function} unregisters the callback
             */
            registerCallback(fn) {
                updateCallbacks.add(fn);
                return () => updateCallbacks.delete(fn);
            },
            /**
             * Registers an element fixed at the top of the page which computes
             * the bottom of the area it covers itself. Other elements only have
             * to be marked with the `o_top_fixed_element` class.
             *
             * @param {HTMLElement} el
             * @param {Function} getCoveredBottom
             * @returns {Function} unregisters the element
             */
            registerTopFixedElement(el, getCoveredBottom) {
                topFixedElements.set(el, getCoveredBottom);
                return () => topFixedElements.delete(el);
            },
            /**
             * @returns {number} the height (in px) covered by the elements
             *      fixed at the top of the page
             */
            getTopFixedOffset() {
                return topFixedOffset;
            },
            /**
             * To call when the top fixed elements change.
             */
            triggerCallbacks() {
                topFixedOffset = computeTopFixedOffset();
                for (const callback of updateCallbacks) {
                    callback(topFixedOffset);
                }
            },
        };
    },
};

registry.category("services").add("website_menus", websiteMenusService);
