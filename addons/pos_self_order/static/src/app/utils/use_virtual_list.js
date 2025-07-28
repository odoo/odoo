import { useState, onMounted, onWillUnmount } from "@odoo/owl";
import { filterWhile } from "@pos_self_order/app/utils";
import { useDeferEffect } from "./use_defer_effect";

/**
 * @typedef {Object} VirtualItem
 * @property {string} _virtualType - Type of the item. The `types.name` from the VirtualList must match this.
 * @property {...any} [props] - Any other properties inherited from the source object.
 */

/**
 * @typedef {Object} VirtualType
 * @property {string} name - The type name (must match `_virtualType` in items).
 * @property {string} selector - CSS selector used to measure item dimensions.
 * @property {boolean} [isMainType] - Whether this type determines the item-per-row calculation.
 */

/**
 * @typedef {Object} VirtualDimensions
 * @property {number} viewportHeight - Visible height of the scroll container.
 * @property {number} viewportWidth - Visible width of the scroll container.
 * @property {number} totalHeight - Total height of all rows combined.
 * @property {Object<string, {height: number, width: number}>} types - Measured dimensions per type (key --> VirtualType.name).
 * @property {number} maxItemsPerRow - Maximum number of items that fit in one row.
 * @property {number} avgRowHeight - Estimated average row height.
 * @property {number} avgItemsPerRow - Estimated average number of items per row.
 */

/**
 * @typedef {Object} VirtualRow
 * @property {number} index - Index of the first item in the row within the base list.
 * @property {string} type - `_virtualType` shared by all items in the row.
 * @property {Array<VirtualItem>} items - Items in this row.
 * @property {number} length - Number of items in this row.
 * @property {number} height - Height of the row in pixels.
 * @property {number} cumulativeHeight - Total height from top of the list to the bottom of this row.
 */

/**
 * @typedef {Object} VirtualList
 * @property {Object} virtual - The virtualized scroll state.
 * @property {Array<VirtualItem>} virtual.items - Currently visible items in the viewport.
 * @property {number} virtual.paddingTop - Height of padding above visible items.
 * @property {number} virtual.paddingBottom - Height of padding below visible items.
 * @property {VirtualDimensions} dimensions - Computed layout values.
 * @property {Array<VirtualRow>} rows - Computed rows (each with index, items, height, etc.)
 */

/**
 * A hook to manage virtual scrolling of a large list of items by computing visible rows,
 * paddings, and efficient slicing of items based on scroll position.
 *
 * @param {Object} config - The configuration object for the virtual list.
 * @param {Object} config.ref - A `useRef` reference to the scrollable container DOM element.
 *   If the element that contains the virtualized items is not the same as the scrollable container,
 *   you can define the inner container using the `.virtual-list-container` class.
 * @param {Array<VirtualItem>} config.items - The full list of items to virtualize (must be a useState.value).
 * @param {Array<VirtualType>} config.types - Metadata for each virtualized item type.
 * @param {number} [config.defaultNumberItems=50] - Initial number of items to render.
 *
 * @returns {VirtualList} An object containing virtualized state and utility functions.
 */
export function useVirtualList({ ref, items: baseItems, types, defaultNumberItems }) {
    // ----- STATE ----- //
    const virtual = useState({
        items: baseItems.value.slice(0, Math.min(defaultNumberItems, baseItems.value.length)),
        paddingTop: 0,
        paddingBottom: 0,
    });
    const rangeIndexes = {
        start: null,
        end: null,
    };
    const dimensions = {
        viewportHeight: 0,
        viewportWidth: 0,
        totalHeight: 0,
        types: {},
        maxItemsPerRow: 0,
        avgRowHeight: 0,
        avgItemsPerRow: 0,
        gapX: 0,
        gapY: 0,
    };
    const rows = [];

    // ----- LIFE CYCLE ----- //
    useDeferEffect(
        () => {
            rangeIndexes.start = null;
            rangeIndexes.end = null;

            computeSizes();
            computeRows();
            virtualizeRows();

            ref.el.scrollTo({ top: 0, behaviour: "instant" });
        },
        () => [baseItems.value]
    );

    onMounted(() => {
        ref.el.addEventListener("scroll", onScroll);
        window.addEventListener("resize", onResize);

        computeSizes();
        computeRows();
        virtualizeRows();
    });

    onWillUnmount(() => {
        ref.el.removeEventListener("scroll", onScroll);
        window.removeEventListener("resize", onResize);
    });
    /**
     * Handles scroll events to update the list of visible items.
     */
    const onScroll = () => {
        virtualizeRows();
    };

    /**
     * Handles resize events to recompute layout and visible items.
     */
    const onResize = () => {
        computeSizes();
        computeRows();
        virtualizeRows();
    };

    /**
     * Computes the viewport size, item dimensions, and max items per row.
     * Updates the `dimensions` object accordingly.
     */
    const computeSizes = () => {
        const container =
            ref.el.querySelector(".virtual-list-container") || ref.el || document.body;
        const containerStyle = window.getComputedStyle(container);

        // Viewport sizes
        dimensions.viewportHeight = ref.el.clientHeight;
        dimensions.viewportWidth = container.clientWidth;

        // Item types
        dimensions.gapX = parseFloat(containerStyle.columnGap || containerStyle.gap || 0);
        dimensions.gapY = parseFloat(containerStyle.rowGap || containerStyle.gap || 0);
        for (const type of types) {
            const element = ref.el.querySelector(type.selector);
            if (element) {
                const style = window.getComputedStyle(element);

                const height =
                    element.clientHeight +
                    parseFloat(style.marginTop || 0) +
                    parseFloat(style.marginBottom || 0) +
                    dimensions.gapY;
                const width =
                    element.clientWidth +
                    parseFloat(style.marginLeft || 0) +
                    parseFloat(style.marginRight || 0) +
                    dimensions.gapX;
                dimensions.types[type.name] = {
                    height: height,
                    width: width,
                };
            }
        }

        // Max items on a row
        const mainType = types.find((type) => type.isMainType);
        const itemWidth =
            dimensions.types[mainType?.name]?.width ||
            Math.min(Object.values(dimensions.types).map((type) => type.width));

        dimensions.maxItemsPerRow = Math.floor(
            (dimensions.viewportWidth + dimensions.gapX) / itemWidth
        );
    };

    /**
     * Computes and populates the `rows` array by grouping items into rows
     * based on their type and the available width. Also calculates average
     * metrics like row height, items per row, and total height.
     */
    const computeRows = () => {
        rows.length = 0;
        let index = 0;
        while (index < baseItems.value.length) {
            // Get row
            const maxRow = baseItems.value.slice(index, index + dimensions.maxItemsPerRow);
            const row = filterWhile(
                maxRow,
                (item, index, array) => index === 0 || array[0]._virtualType === item._virtualType
            );
            if (row.length === 0) {
                break;
            }

            // Compute Height
            const rowType = row[0]._virtualType;
            const height = dimensions.types[rowType]?.height || 0;
            const cumulativeHeight = (rows[rows.length - 1]?.cumulativeHeight || 0) + height;

            // Next row
            rows.push({
                index,
                type: rowType,
                items: row,
                length: row.length,
                height,
                cumulativeHeight,
            });
            index += row.length;
        }

        // Gap
        const lastRow = rows[rows.length - 1];
        if (lastRow) {
            lastRow.height -= dimensions.gapY;
            lastRow.cumulativeHeight -= dimensions.gapY;
        }

        // Averages
        dimensions.totalHeight = lastRow?.cumulativeHeight || 0;
        dimensions.avgRowHeight = dimensions.totalHeight / Math.max(rows.length, 1);
        dimensions.avgItemsPerRow = baseItems.value.length / Math.max(rows.length, 1);
    };

    /**
     * Updates the virtualized list of visible items based on the current scroll position.
     * Calculates which items should be rendered, along with top and bottom paddings
     * to preserve scroll height.
     */
    const virtualizeRows = () => {
        // Define range
        const scrollTop = ref.el.scrollTop;
        const yStart = Math.max(0, scrollTop - dimensions.viewportHeight);
        const yEnd = scrollTop + dimensions.viewportHeight * 2;

        // Get start/end indexes
        const indexRowStart = Math.floor(yStart / dimensions.avgRowHeight);
        const indexRowEnd = Math.ceil(yEnd / dimensions.avgRowHeight);

        const startItemIndex = getStartIndex(indexRowStart * dimensions.avgItemsPerRow);
        const endItemIndex = getEndIndex(indexRowEnd * dimensions.avgItemsPerRow);

        // Did not change
        if (rangeIndexes.start === startItemIndex && rangeIndexes.end === endItemIndex) {
            return;
        }
        rangeIndexes.start = startItemIndex;
        rangeIndexes.end = endItemIndex;

        // Update virtual items
        const items = baseItems.value.slice(startItemIndex, endItemIndex);
        const rowStart = rows.find((row) => row.index === startItemIndex);
        const rowEnd = endItemIndex ? rows.find((row) => row.index === endItemIndex) : rows.at(-1);
        const paddingTop = rowStart ? rowStart.cumulativeHeight - rowStart.height : 0;
        const paddingBottom = rowEnd
            ? dimensions.totalHeight -
              (rowEnd.cumulativeHeight - (endItemIndex ? rowEnd.height : 0))
            : 0;

        virtual.items = items;
        virtual.paddingTop = paddingTop;
        virtual.paddingBottom = paddingBottom;
    };

    /**
     * Returns the index of the first item in the row just before or equal to the given index.
     * Used to determine the starting point for virtualized rendering.
     * @param {number} index - Index from the base items.
     * @returns {number} - Index in the base items array where the corresponding row starts.
     */
    const getStartIndex = (index) => {
        index = Math.max(0, Math.floor(index));

        for (let i = 1; i < rows.length; i++) {
            if (rows[i].index > index) {
                return rows[i - 1].index;
            }
        }
        return rows[rows.length - 1]?.index || 0;
    };

    /**
     * Returns the index of the first item in the row just after the given index.
     * Used to determine the ending point for virtualized rendering.
     *
     * @param {number} index - Index from the base items.
     * @returns {number | undefined} - Index in the base items array where the next row starts or `undefined` if the last row must be rendered.
     */
    const getEndIndex = (index) => {
        index = Math.max(0, Math.ceil(index));

        for (let i = 1; i < rows.length; i++) {
            if (rows[i].index > index) {
                return rows[i].index;
            }
        }
        return undefined;
    };

    return { virtual, dimensions, rows };
}
