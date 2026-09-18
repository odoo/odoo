import { computed, signal, useListener } from "@odoo/owl";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * Computes the start and end indices of the visible items in a virtual list.
 * This works both horizontally (start = scroll left, span = window width) and
 * vertically (start = scroll top, span = window height).
 *
 * @param {number[]} sizes cumulative sizes of the items
 * @param {number} start starting position (in pixels) of the visible area
 * @param {number} span size (in pixels) of the visible area
 * @param {number} prevStartIndex previous start index, used to optimize the calculation
 * @param {number} bufferCoef coefficient used to compute buffer size
 */
function computeIndices(sizes, start, span, prevStartIndex, bufferCoef) {
    if (!sizes.length) {
        return {
            start: null,
            end: null,
        };
    }
    if (sizes.at(-1) < span) {
        // all items could be displayed
        return {
            start: 0,
            end: sizes.length - 1,
        };
    }
    const bufferSize = Math.ceil(span * bufferCoef);
    const bufferStart = start - bufferSize;
    const bufferEnd = start + span + bufferSize;

    // search the first index such that sizes[index] > bufferStart
    let startIndex = prevStartIndex || 0;
    while (startIndex > 0 && sizes[startIndex] > bufferStart) {
        startIndex--;
    }
    while (startIndex < sizes.length - 1 && sizes[startIndex] <= bufferStart) {
        startIndex++;
    }

    // search the last index such that (sizes[index - 1] || 0) < bufferEnd
    let endIndex = startIndex;
    while (endIndex < sizes.length - 1 && (sizes[endIndex - 1] || 0) < bufferEnd) {
        endIndex++;
    }
    while (endIndex > startIndex && (sizes[endIndex - 1] || 0) >= bufferEnd) {
        endIndex--;
    }

    return {
        start: startIndex,
        end: endIndex,
    };
}

/**
 * @param {number[]} values
 */
function getSummed(values) {
    let acc = 0;
    return values.map((w) => (acc += w));
}

/**
 * Sizes can be given either as a static array, or as a getter returning an array.
 * In the latter case, the getter is called from inside a computed, so any reactive
 * value it reads makes the sizes recompute on demand.
 *
 * @param {number[] | (() => number[]) | undefined} sizes
 * @returns {number[]}
 */
function evaluateSizes(sizes) {
    return (typeof sizes === "function" ? sizes() : sizes) || [];
}

const DEFAULT_BUFFER_COEFFICIENT = 1;

/**
 * Calculates which items should be displayed in a given grid. It works by receiving
 * informations about row widths and/or column heights, and returning the **first**
 * and **last** indices (for each direction) of the items that should be actually
 * rendered.
 *
 * Requirements:
 *  - the scrollable area has a fixed height and width.
 *  - the items are rendered with a proper offset inside the scrollable area.
 *      e.g. using CSS `grid` properties or absolute positioning
 *
 * The returned `scrollableRef` property should be given in a `t-ref` directive
 * to the scrollable element.
 *
 * @param {Object} params
 * @param {import("@odoo/owl").ReactiveValue<HTMLElement>} params.scrollableRef signal
 * @param {number[] | (() => number[])} [params.rowHeights] row heights, either a
 *  static array or a getter. Prefer the getter form when the heights derive from
 *  reactive values (props, signals, ...): they are then recomputed on demand,
 *  which guarantees the visible window is in sync with the data during the very
 *  render that changed it, instead of one render later.
 * @param {number[] | (() => number[])} [params.columnWidths] column widths, same as above
 *  pointing to the scrollable element. It is optional, as this hook can spawn a
 *  new one if needed, that will be available in the return value.
 * @param {{ left?: number; top?: number }} [params.initialScroll] initial scroll
 *  position of the scrollable element
 * @param {number} [params.bufferCoef=1] coefficient used to calculate the buffer
 *  size around the visible area; with its default value of 1, it means that the
 *  resulting buffer size is equal to the size of the window, and that the whole
 *  rendered area will be 3 times the window size.
 *  As this works in both dimensions, this could mean that a total area of 9 windows
 *  (3x3) would be rendered.
 *  Consider using a lower value if the rendering becomse too costly.
 *  Setting it to 0 removes the buffer entirely.
 */
export function useVirtualGrid({
    scrollableRef,
    rowHeights,
    columnWidths,
    initialScroll,
    bufferCoef,
}) {
    function onResize() {
        innerWidth.set(window.innerWidth);
        innerHeight.set(window.innerHeight);
    }

    /**
     * @param {Event & { currentTarget: HTMLElement }} ev
     */
    function onScroll(ev) {
        scrollLeft.set(ev.currentTarget.scrollLeft);
        scrollTop.set(ev.currentTarget.scrollTop);
    }

    bufferCoef ||= DEFAULT_BUFFER_COEFFICIENT;

    // Columns reactive values
    const columnIndices = computed(function computeColumnIndices() {
        const indices = computeIndices(
            summedColumnWidths(),
            Math.abs(scrollLeft()),
            innerWidth(),
            lastColumnStartIndex,
            bufferCoef
        );
        lastColumnStartIndex = indices.start;
        return indices;
    });
    const firstColumn = computed(() => columnIndices().start);
    const lastColumn = computed(() => columnIndices().end);
    const columnWidthsOverride = signal(null);
    const summedColumnWidths = computed(() =>
        getSummed(columnWidthsOverride() ?? evaluateSizes(columnWidths))
    );
    let lastColumnStartIndex = 0;

    // Rows reactive values
    const rowIndices = computed(function computeRowIndices() {
        const indices = computeIndices(
            summedRowHeights(),
            Math.abs(scrollTop()),
            innerHeight(),
            lastRowStartIndex,
            bufferCoef
        );
        lastRowStartIndex = indices.start;
        return indices;
    });
    const firstRow = computed(() => rowIndices().start);
    const lastRow = computed(() => rowIndices().end);
    const rowHeightsOverride = signal(null);
    const summedRowHeights = computed(() =>
        getSummed(rowHeightsOverride() ?? evaluateSizes(rowHeights))
    );
    let lastRowStartIndex = 0;

    // "External" reactive values (i.e.: scroll position & window size)
    const innerWidth = signal(window.innerWidth);
    const innerHeight = signal(window.innerHeight);
    const scrollLeft = signal(initialScroll?.left || 0);
    const scrollTop = signal(initialScroll?.top || 0);

    useListener(scrollableRef, "scroll", useThrottleForAnimation(onScroll));
    useListener(window, "resize", useThrottleForAnimation(onResize));

    return {
        firstRow,
        lastRow,
        firstColumn,
        lastColumn,
        /**
         * Sets the width of each column.
         * Indexes should match the indexes of the columns.
         *
         * Only useful when `columnWidths` was not given as a getter: it takes
         * precedence over the `columnWidths` parameter from then on.
         *
         * @param {number[]} widths
         */
        setColumnWidths(widths) {
            columnWidthsOverride.set(widths);
        },
        /**
         * Sets the height of each row.
         * Indexes should match the indexes of the rows.
         *
         * Only useful when `rowHeights` was not given as a getter: it takes
         * precedence over the `rowHeights` parameter from then on.
         *
         * @param {number[]} heights
         */
        setRowHeights(heights) {
            rowHeightsOverride.set(heights);
        },
    };
}
