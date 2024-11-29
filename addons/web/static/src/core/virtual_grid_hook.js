import { useComponent, useEffect, useExternalListener } from "@odoo/owl";
import { pick, shallowEqual } from "@web/core/utils/objects";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * @template T
 * @typedef VirtualGridParams
 * @property {ReturnType<typeof import("@odoo/owl").useRef>} scrollableRef
 *  a ref to the scrollable element
 * @property {ScrollPosition} [initialScroll={ left: 0, top: 0 }]
 *  the initial scroll position of the scrollable element
 * @property {(changed: Partial<VirtualGridIndexes>) => void} [onChange=() => this.render()]
 *  a callback called when the visible items change, i.e. when on scroll or resize.
 *  the default implementation is to re-render the component.
 * @property {number} [bufferCoef=1]
 *  the coefficient to calculate the buffer size around the visible area.
 *  The buffer size is equal to bufferCoef * windowSize.
 *  The default value is 1: it means that the buffer size takes one more window size on each side.
 *  So the whole area that will be rendered is 3 times the window size.
 *  If you use each direction, it could be up to 9 times the window size (3x3).
 *  Consider lowering this value if you have a costful rendering.
 *  A value of 0 means no buffer.
 */

/**
 * @typedef VirtualGridIndexes
 * @property {[number, number] | undefined} columnsIndexes
 * @property {[number, number] | undefined} rowsIndexes
 */

/**
 * @typedef VirtualGridSetters
 * @property {(widths: number[]) => void} setColumnsWidths
 *  Use it to set the width of each column.
 *  Indexes should match the indexes of the columns.
 * @property {(heights: number[]) => void} setRowsHeights
 *  Use it to set the height of each row.
 *  Indexes should match the indexes of the rows.
 */

/**
 * @typedef ScrollPosition
 * @property {number} left
 * @property {number} top
 */

const BUFFER_COEFFICIENT = 1;

/**
 * @typedef GetIndexesParams
 * @property {number[]} sizes contains the sizes of the items. Each size is the sum of the sizes of the previous items and the size of the current item.
 * @property {number} start it is the start position of the visible area, here it is the scroll position.
 * @property {number} span it is the size of the visible area, here it is the window size.
 * @property {number} [prevStartIndex] the previous start index, it is used to optimize the calculation.
 * @property {number} [bufferCoef=BUFFER_COEFFICIENT] the coefficient to calculate the buffer size.
 */

/**
 * This function calculates the indexes of the visible items in a virtual list.
 *
 * @param {GetIndexesParams} param0
 * @returns {[number, number] | undefined} the indexes of the visible items with a surrounding buffer of totalSize on each side.
 */
function getIndexes({ sizes, start, span, prevStartIndex, bufferCoef = BUFFER_COEFFICIENT }) {
    if (!sizes || !sizes.length) {
        return [];
    }
    if (sizes.at(-1) < span) {
        // all items could be displayed
        return [0, sizes.length - 1];
    }
    const bufferSize = Math.round(span * bufferCoef);
    const bufferStart = start - bufferSize;
    const bufferEnd = start + span + bufferSize;

    let startIndex = prevStartIndex ?? 0;
    // we search the first index such that sizes[index] > bufferStart
    while (startIndex > 0 && sizes[startIndex] > bufferStart) {
        startIndex--;
    }
    while (startIndex < sizes.length - 1 && sizes[startIndex] <= bufferStart) {
        startIndex++;
    }

    let endIndex = startIndex;
    // we search the last index such that (sizes[index - 1] ?? 0) < bufferEnd
    while (endIndex < sizes.length - 1 && (sizes[endIndex - 1] ?? 0) < bufferEnd) {
        endIndex++;
    }
    while (endIndex > startIndex && (sizes[endIndex - 1] ?? 0) >= bufferEnd) {
        endIndex--;
    }
    return [startIndex, endIndex];
}

/**
 * Calculates the displayed items in a virtual grid.
 *
 * Requirements:
 *  - the scrollable area has a fixed height and width.
 *  - the items are rendered with a proper offset inside the scrollable area.
 *    This can be achieved e.g. with a css grid or an absolute positioning.
 *
 * @template T
 * @param {VirtualGridParams<T>} params
 * @returns {VirtualGridIndexes & VirtualGridSetters}
 */
export function useVirtualGrid({ scrollableRef, initialScroll, onChange, bufferCoef }) {
    const comp = useComponent();
    onChange ||= () => comp.render();

    const current = { scroll: { left: 0, top: 0, ...initialScroll } };
    const computeColumnsIndexes = () => {
        return getIndexes({
            sizes: current.summedColumnsWidths,
            start: Math.abs(current.scroll.left),
            span: window.innerWidth,
            prevStartIndex: current.columnsIndexes?.[0],
            bufferCoef,
        });
    };
    const computeRowsIndexes = () => {
        return getIndexes({
            sizes: current.summedRowsHeights,
            start: current.scroll.top,
            span: window.innerHeight,
            prevStartIndex: current.rowsIndexes?.[0],
            bufferCoef,
        });
    };
    const throttledCompute = useThrottleForAnimation(() => {
        const changed = [];
        const columnsVisibleIndexes = computeColumnsIndexes();
        if (!shallowEqual(columnsVisibleIndexes, current.columnsIndexes)) {
            current.columnsIndexes = columnsVisibleIndexes;
            changed.push("columnsIndexes");
        }
        const rowsVisibleIndexes = computeRowsIndexes();
        if (!shallowEqual(rowsVisibleIndexes, current.rowsIndexes)) {
            current.rowsIndexes = rowsVisibleIndexes;
            changed.push("rowsIndexes");
        }
        if (changed.length) {
            onChange(pick(current, ...changed));
        }
    });
    const scrollListener = (/** @type {Event & { target: Element }} */ ev) => {
        current.scroll.left = ev.target.scrollLeft;
        current.scroll.top = ev.target.scrollTop;
        throttledCompute();
    };
    useEffect(
        (el) => {
            el?.addEventListener("scroll", scrollListener);
            return () => el?.removeEventListener("scroll", scrollListener);
        },
        () => [scrollableRef.el]
    );
    useExternalListener(window, "resize", () => throttledCompute());
    return {
        get columnsIndexes() {
            return current.columnsIndexes;
        },
        get rowsIndexes() {
            return current.rowsIndexes;
        },
        setColumnsWidths(widths) {
            let acc = 0;
            current.summedColumnsWidths = widths.map((w) => (acc += w));
            delete current.columnsIndexes;
            current.columnsIndexes = computeColumnsIndexes();
        },
        setRowsHeights(heights) {
            let acc = 0;
            current.summedRowsHeights = heights.map((h) => (acc += h));
            delete current.rowsIndexes;
            current.rowsIndexes = computeRowsIndexes();
        },
    };
}
