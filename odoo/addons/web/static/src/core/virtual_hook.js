/** @odoo-module **/

import {
    onWillRender,
    onWillStart,
    toRaw,
    useEffect,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { shallowEqual } from "@web/core/utils/arrays";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * @template T
 * @typedef VirtualHookParams
 * @property {() => T[]} getItems
 *  a getter for the array of all items
 * @property {(item: T) => number} getItemHeight
 *  a getter for the height of a given item.
 *  The height should be a number of pixels.
 * @property {ReturnType<typeof import("@odoo/owl").useRef>} scrollableRef
 *  a ref to the scrollable element
 * @property {ScrollPosition} [initialScroll={ top: 0 }]
 *  the initial scroll position of the scrollable element
 */

/**
 * @typedef ScrollPosition
 * @property {number} top
 */

/**
 * Calculates the displayed items in a virtual list.
 *
 * Requirements:
 *  - the scrollable area has a fixed height
 *  - the items are rendered with a proper offset inside the scrollable area.
 *    This can be achieved e.g. with a css grid or an absolute positioning.
 *
 * @template T
 * @param {VirtualHookParams<T>} params
 * @returns {ReturnType<useState<T>>}
 */
export function useVirtual({ getItems, scrollableRef, initialScroll, getItemHeight }) {
    const computeVirtualItems = () => {
        const { items, scroll } = current;

        const yStart = scroll.top - window.innerHeight;
        const yEnd = scroll.top + 2 * window.innerHeight;

        let [startIndex, endIndex] = [0, 0];
        let currentTop = 0;

        for (const item of items) {
            const height = getItemHeight(item);
            if (currentTop + height < yStart) {
                startIndex++;
                endIndex++;
            } else if (currentTop + height <= yEnd + height) {
                endIndex++;
            } else {
                break;
            }
            currentTop += height;
        }

        const prevItems = toRaw(virtualItems);
        const newItems = items.slice(startIndex, endIndex);

        if (!shallowEqual(prevItems, newItems)) {
            virtualItems.length = 0;
            virtualItems.push(...newItems);
        }
    };

    const current = {
        items: getItems(),
        scroll: { top: 0, ...initialScroll },
    };

    const virtualItems = useState([]);

    onWillStart(computeVirtualItems);
    onWillRender(() => {
        const previousItems = current.items;
        current.items = getItems();
        if (!shallowEqual(previousItems, current.items)) {
            computeVirtualItems();
        }
    });
    const throttledCompute = useThrottleForAnimation(computeVirtualItems);
    const scrollListener = (/** @type {Event & { target: Element }} */ ev) => {
        current.scroll.top = ev.target.scrollTop;
        throttledCompute();
    };
    useExternalListener(window, "resize", throttledCompute);
    useEffect(
        (el) => {
            if (el) {
                el.addEventListener("scroll", scrollListener);
                return () => el.removeEventListener("scroll", scrollListener);
            }
        },
        () => [scrollableRef.el]
    );

    return virtualItems;
}
