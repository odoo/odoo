/** @odoo-module **/

import { onWillRender, onWillStart, toRaw, useEffect, useState } from "@odoo/owl";
import { shallowEqual } from "./utils/arrays";
import { throttleForAnimation } from "./utils/timing";

/**
 * @template T
 * @typedef VirtualHookParams
 * @property {T[] | () => T[]} items
 * @property {typeof useRef} scrollableRef
 * @property {ScrollPosition} [initialScroll={ left: 0, top: 0 }]
 * @property {PixelValue | (item: T) => PixelValue} [itemHeight=0]
 * @property {PixelValue | (item: T) => PixelValue} [itemWidth=0]
 * @property {PixelValue} [margin="100%"]
 */

/**
 * @typedef ScrollPosition
 * @property {number} left
 * @property {number} top
 */

/** @typedef {number | `${string}px` | `${string}%`} PixelValue */

/**
 * Converts a number,
 *
 * @param {{ width: PixelValue } | { height: PixelValue }} propValue
 * @returns {number}
 */
const toPixels = (propValue) => {
    const [prop, value] = Object.entries(propValue)[0];
    if (typeof value === "number") {
        return value;
    }
    if (value.endsWith("%")) {
        const size = prop === "width" ? window.innerWidth : window.innerHeight;
        return size * (Number(value.slice(0, -1)) / 100);
    }
    if (value.endsWith("px")) {
        return Number(value.slice(0, -2));
    }
};

/**
 * Calculates the displayed items in a virtual list.
 *
 * @template T
 * @param {VirtualHookParams<T>} params
 * @returns {ReturnType<useState<T>>}
 */
export function useVirtual({ items, scrollableRef, initialScroll, itemHeight, itemWidth, margin }) {
    const computeVirtualItems = () => {
        const { items, scroll } = current;

        const xStart = scroll.left - xMargin;
        const xEnd = scroll.left + window.innerWidth + xMargin;

        const yStart = scroll.top - yMargin;
        const yEnd = scroll.top + window.innerHeight + yMargin;

        let [startIndex, endIndex] = [0, 0];
        let [currentLeft, currentTop] = [0, 0];

        for (const item of items) {
            const width = toPixels({ width: getItemWidth(item) });
            const height = toPixels({ height: getItemHeight(item) });
            if (currentLeft + width < xStart || currentTop + height < yStart) {
                startIndex++;
                endIndex++;
            } else if (currentLeft - width <= xEnd || currentTop - height <= yEnd) {
                endIndex++;
            } else {
                break;
            }
            currentLeft += width;
            currentTop += height;
        }

        const prevItems = toRaw(virtualItems);
        const newItems = items.slice(startIndex, endIndex);

        if (!shallowEqual(prevItems, newItems)) {
            virtualItems.length = 0;
            virtualItems.push(...newItems);
        }
    };

    const getItems = typeof items === "function" ? items : () => items;

    const getItemHeight =
        typeof itemHeight === "function" ? itemHeight : () => itemHeight || "100%";

    const getItemWidth = typeof itemWidth === "function" ? itemWidth : () => itemWidth || "100%";

    const marginValue = margin === undefined ? "100%" : margin;
    const xMargin = toPixels({ width: marginValue });
    const yMargin = toPixels({ height: marginValue });

    const current = {
        items: getItems(),
        scroll: { left: 0, top: 0, ...initialScroll },
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
    const throttledOnScroll = throttleForAnimation((/** @type {Event} */ ev) => {
        current.scroll.left = ev.target.scrollLeft;
        current.scroll.top = ev.target.scrollTop;
        computeVirtualItems();
    });
    useEffect(
        (el) => {
            if (el) {
                el.addEventListener("scroll", throttledOnScroll);
                return () => el.removeEventListener("scroll", throttledOnScroll);
            }
        },
        () => [scrollableRef.el]
    );

    return virtualItems;
}
