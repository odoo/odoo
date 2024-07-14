/** @odoo-module **/

import { useEffect } from "@odoo/owl";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { clamp } from "@web/core/utils/numbers";
import { pick } from "@web/core/utils/objects";

/** @typedef {luxon.DateTime} DateTime */

/**
 * @param {number} target
 * @param {number[]} values
 * @returns {number}
 */
function closest(target, values) {
    return values.reduce(
        (prev, val) => (Math.abs(val - target) < Math.abs(prev - target) ? val : prev),
        Infinity
    );
}

/**
 * Adds a time diff to a date keeping the same value even if the offset changed
 * during the manipulation. This is typically needed with timezones using DayLight
 * Saving offset changes.
 *
 * @example dateAddFixedOffset(luxon.DateTime.local(), { hour: 1 });
 * @param {DateTime} date
 * @param {Record<string, number>} plusParams
 */
export function dateAddFixedOffset(date, plusParams) {
    const initialOffset = date.offset;
    const shouldApplyOffset = Object.keys(plusParams).some((key) =>
        /^(day|hour|minute|(milli)?second)s?$/i.test(key)
    );
    const result = date.plus(plusParams);
    const diff = initialOffset - result.offset;
    if (shouldApplyOffset && diff) {
        const adjusted = result.plus({ minute: diff });
        return adjusted.offset === initialOffset ? result : adjusted;
    } else {
        return result;
    }
}

/**
 * @param {number} cellPart
 * @param {(0 | 1)[]} subSlotUnavailabilities
 * @param {boolean} isToday
 * @returns {string | null}
 */
export function getCellColor(cellPart, subSlotUnavailabilities, isToday) {
    const sum = subSlotUnavailabilities.reduce((acc, d) => acc + d);
    if (!sum) {
        return null;
    }
    switch (cellPart) {
        case sum: {
            return `background-color:${getCellPartColor(sum, isToday)}`;
        }
        case 2: {
            const [c0, c1] = subSlotUnavailabilities.map((d) => getCellPartColor(d, isToday));
            return `background:linear-gradient(90deg,${c0}49%,${c1}50%)`;
        }
        case 4: {
            const [c0, c1, c2, c3] = subSlotUnavailabilities.map((d) =>
                getCellPartColor(d, isToday)
            );
            return `background:linear-gradient(90deg,${c0}24%,${c1}25%,${c1}49%,${c2}50%,${c2}74%,${c3}75%)`;
        }
    }
}

/**
 * @param {0 | 1} availability
 * @param {boolean} isToday
 * @returns {string}
 */
export function getCellPartColor(availability, isToday) {
    if (availability) {
        return "var(--Gantt__DayOff-background-color)";
    } else if (isToday) {
        return "var(--Gantt__DayOffToday-background-color)";
    } else {
        return "var(--Gantt__Day-background-color)";
    }
}

/**
 * @param {number | [number, string]} value
 * @returns {number}
 */
export function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % NB_GANTT_RECORD_COLORS;
    } else if (Array.isArray(value)) {
        return value[0] % NB_GANTT_RECORD_COLORS;
    }
    return 0;
}

/**
 * Intervals are supposed to intersect (intersection duration >= 1 milliseconds)
 *
 * @param {[DateTime, DateTime]} interval
 * @param {[DateTime, DateTime]} otherInterval
 * @returns {[DateTime, DateTime]}
 */
export function getIntersection(interval, otherInterval) {
    const [start, end] = interval;
    const [otherStart, otherEnd] = otherInterval;
    return [start >= otherStart ? start : otherStart, end <= otherEnd ? end : otherEnd];
}

/**
 * Computes intersection of a closed interval with a union of closed intervals ordered and disjoint
 * = a union of intersections
 *
 * @param {[DateTime, DateTime]} interval
 * @param {[DateTime, DateTime]} intervals
 * @returns {[DateTime, DateTime][]}
 */
export function getUnionOfIntersections(interval, intervals) {
    const [start, end] = interval;
    const intersecting = intervals.filter((otherInterval) => {
        const [otheStart, otherEnd] = otherInterval;
        return otherEnd > start && end > otheStart;
    });
    const len = intersecting.length;
    if (len === 0) {
        return [];
    }
    const union = [];
    const first = getIntersection(interval, intersecting[0]);
    union.push(first);
    if (len >= 2) {
        const last = getIntersection(interval, intersecting[len - 1]);
        union.push(...intersecting.slice(1, len - 1), last);
    }
    return union;
}

/**
 * @param {Object} params
 * @param {Ref<HTMLElement>} params.ref
 * @param {string} params.selector
 * @param {string} params.related
 * @param {string} params.className
 */
export function useMultiHover({ ref, selector, related, className }) {
    /**
     * @param {HTMLElement} el
     */
    const findSiblings = (el) =>
        ref.el.querySelectorAll(
            related
                .map((attr) => `[${attr}='${el.getAttribute(attr).replace(/'/g, "\\'")}']`)
                .join("")
        );

    /**
     * @param {PointerEvent} ev
     */
    const onPointerEnter = (ev) => {
        for (const sibling of findSiblings(ev.target)) {
            sibling.classList.add(...classList);
            classedEls.add(sibling);
        }
    };

    /**
     * @param {PointerEvent} ev
     */
    const onPointerLeave = (ev) => {
        for (const sibling of findSiblings(ev.target)) {
            sibling.classList.remove(...classList);
            classedEls.delete(sibling);
        }
    };

    const classList = className.split(/\s+/g);
    const classedEls = new Set();

    useEffect(
        (...targets) => {
            if (targets.length) {
                for (const target of targets) {
                    target.addEventListener("pointerenter", onPointerEnter);
                    target.addEventListener("pointerleave", onPointerLeave);
                }
                return () => {
                    for (const el of classedEls) {
                        el.classList.remove(...classList);
                    }
                    classedEls.clear();
                    for (const target of targets) {
                        target.removeEventListener("pointerenter", onPointerEnter);
                        target.removeEventListener("pointerleave", onPointerLeave);
                    }
                };
            }
        },
        () => [...ref.el.querySelectorAll(selector)]
    );
}

const NB_GANTT_RECORD_COLORS = 12;

// Resizable hook handles

const HANDLE_CLASS_START = "o_handle_start";
const HANDLE_CLASS_END = "o_handle_end";
const handles = {
    start: document.createElement("div"),
    end: document.createElement("div"),
};

// Draggable hooks

export const useGanttConnectorDraggable = makeDraggableHook({
    name: "useGanttConnectorDraggable",
    acceptedParams: {
        parentWrapper: [String],
    },
    onComputeParams({ ctx, params }) {
        ctx.parentWrapper = params.parentWrapper;
        ctx.followCursor = false;
    },
    onDragStart: ({ ctx, addStyle }) => {
        const { current } = ctx;
        const parent = current.element.closest(ctx.parentWrapper);
        if (!parent) {
            return;
        }
        for (const otherParent of ctx.ref.el.querySelectorAll(ctx.parentWrapper)) {
            if (otherParent !== parent) {
                addStyle(otherParent, { pointerEvents: "auto" });
            }
        }
        return { initialPosition: current.initialPosition, sourcePill: parent };
    },
    onDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragEnd: ({ ctx }) => pick(ctx.current, "element"),
    onDrop: ({ ctx, target }) => {
        const { current } = ctx;
        const parent = current.element.closest(ctx.parentWrapper);
        const targetParent = target.closest(ctx.parentWrapper);
        if (!targetParent || targetParent === parent) {
            return;
        }
        return { target: targetParent };
    },
});

export const useGanttDraggable = makeDraggableHook({
    name: "useGanttDraggable",
    acceptedParams: {
        cells: [String, Function],
        cellDragClassName: [String, Function],
        ghostClassName: [String, Function],
        hoveredCell: [Object],
    },
    onComputeParams({ ctx, params }) {
        ctx.cellSelector = params.cells;
        ctx.ghostClassName = params.ghostClassName;
        ctx.cellDragClassName = params.cellDragClassName;
        ctx.hoveredCell = params.hoveredCell;
    },
    onDragStart({ ctx, addStyle }) {
        const { cellSelector, current, ghostClassName } = ctx;
        for (const cell of ctx.ref.el.querySelectorAll(cellSelector)) {
            addStyle(cell, { pointerEvents: "auto" });
        }
        current.element.before(current.placeHolder);
        if (ghostClassName) {
            current.placeHolder.classList.add(ghostClassName);
        }
        return { pill: current.element };
    },
    onDrag({ ctx, addStyle }) {
        const { cellSelector, current, hoveredCell } = ctx;
        let { el: cell, part } = hoveredCell;

        const isDifferentCell = cell !== current.cell.el;
        const isDifferentPart = part !== current.cell.part;

        if (cell && !cell.matches(cellSelector)) {
            cell = null; // Not a cell
        }

        current.cell.el = cell;
        current.cell.part = part;

        if (cell) {
            // Recompute cell style if in a different cell
            if (isDifferentCell) {
                const style = getComputedStyle(cell);
                current.cell.gridRow = style.getPropertyValue("grid-row");
                current.cell.gridColumnStart =
                    Number(style.getPropertyValue("grid-column-start")) + current.gridColumnOffset;
            }
            // Assign new grid coordinates if in different cell or different cell part
            if (isDifferentCell || isDifferentPart) {
                const { gridColumnEnd } = current;
                const { gridRow, gridColumnStart: start } = current.cell;
                const gridColumnStart = clamp(start + part, 1, current.maxGridColumnStart);

                addStyle(current.cellGhost, { gridRow, gridColumnStart, gridColumnEnd });

                current.cell.index = gridColumnStart - 1; // Grid incides start at 1
            }
        } else {
            current.cell.index = null;
        }

        // Attach or remove cell ghost
        if (isDifferentCell) {
            if (cell) {
                cell.after(current.cellGhost);
            } else {
                current.cellGhost.remove();
            }
        }

        return { pill: current.element };
    },
    onDragEnd({ ctx }) {
        return { pill: ctx.current.element };
    },
    onDrop({ ctx }) {
        const { cell, element, initialIndex } = ctx.current;
        if (cell.index !== null) {
            return {
                pill: element,
                cell: cell.el,
                diff: cell.index - initialIndex,
            };
        }
    },
    onWillStartDrag({ ctx, addCleanup, addStyle }) {
        const { current } = ctx;
        const { el: cell, part } = ctx.hoveredCell;

        current.placeHolder = current.element.cloneNode(true);
        current.cellGhost = document.createElement("div");
        current.cellGhost.className = ctx.cellDragClassName;
        current.cell = { el: null, index: null, part: 0 };

        const gridStyle = getComputedStyle(cell.parentElement);
        const pillStyle = getComputedStyle(current.element);
        const cellStyle = getComputedStyle(cell);

        const gridTemplateColumns = gridStyle.getPropertyValue("grid-template-columns");
        const pGridColumnStart = Number(pillStyle.getPropertyValue("grid-column-start"));
        const pGridColumnEnd = pillStyle.getPropertyValue("grid-column-end");
        const cGridColumnStart = Number(cellStyle.getPropertyValue("grid-column-start")) + part;
        const spanMatch = pGridColumnEnd.match(/span (\d+)/);
        const highestGridIndex = gridTemplateColumns.split(" ").length + 1;
        const pillSpan = spanMatch ? Number(spanMatch[1]) : 1;

        current.initialIndex = pGridColumnStart - 1;
        current.maxGridColumnStart = highestGridIndex - pillSpan;
        current.gridColumnOffset = pGridColumnStart - cGridColumnStart;
        current.gridColumnEnd = pillStyle.getPropertyValue("grid-column-end");

        addStyle(ctx.ref.el, { pointerEvents: "auto" });
        addCleanup(() => {
            current.placeHolder.remove();
            current.cellGhost.remove();
        });
    },
});

export const useGanttUndraggable = makeDraggableHook({
    name: "useGanttUndraggable",
    onDragStart({ ctx }) {
        return { pill: ctx.current.element };
    },
    onDragEnd({ ctx }) {
        return { pill: ctx.current.element };
    },
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        const { x, y, width, height } = getRect(ctx.current.element);
        ctx.current.container = document.createElement("div");

        addStyle(ctx.ref.el, { pointerEvents: "auto" });
        addStyle(ctx.current.container, {
            position: "fixed",
            left: `${x}px`,
            top: `${y}px`,
            width: `${width}px`,
            height: `${height}px`,
        });

        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
});

export const useGanttResizable = makeDraggableHook({
    name: "useGanttResizable",
    requiredParams: ["handles"],
    acceptedParams: {
        innerPills: [String, Function],
        handles: [String, Function],
        rtl: [Boolean, Function],
        cells: [String, Function],
        precision: [Number, Function],
        showHandles: [Function],
    },
    onComputeParams({ ctx, params, addCleanup, addEffectCleanup, getRect }) {
        const onElementPointerEnter = (ev) => {
            if (ctx.dragging || ctx.willDrag) {
                return;
            }

            const pill = ev.target;
            const innerPill = pill.querySelector(params.innerPills);

            const pillRect = getRect(innerPill);

            for (const el of Object.values(handles)) {
                el.style.height = `${pillRect.height}px`;
            }

            const showHandles = params.showHandles ? params.showHandles(pill) : {};
            if ("start" in showHandles && !showHandles.start) {
                handles.start.remove();
            } else {
                innerPill.appendChild(handles.start);
            }
            if ("end" in showHandles && !showHandles.end) {
                handles.end.remove();
            } else {
                innerPill.appendChild(handles.end);
            }
        };

        const onElementPointerLeave = () => {
            const remove = () => Object.values(handles).forEach((h) => h.remove());
            if (ctx.dragging || ctx.current.element) {
                addCleanup(remove);
            } else {
                remove();
            }
        };

        ctx.cellSelector = params.cells;
        ctx.precision = params.precision;
        ctx.rtl = params.rtl;

        for (const el of ctx.ref.el.querySelectorAll(params.elements)) {
            el.addEventListener("pointerenter", onElementPointerEnter);
            el.addEventListener("pointerleave", onElementPointerLeave);
            addEffectCleanup(() => {
                el.removeEventListener("pointerenter", onElementPointerEnter);
                el.removeEventListener("pointerleave", onElementPointerLeave);
            });
        }

        handles.start.className = `${params.handles} ${HANDLE_CLASS_START}`;
        handles.start.style.cursor = `${params.rtl ? "e" : "w"}-resize`;

        handles.end.className = `${params.handles} ${HANDLE_CLASS_END}`;
        handles.end.style.cursor = `${params.rtl ? "w" : "e"}-resize`;

        // Override "full" and "element" selectors: we want the draggable feature
        // to apply to the handles
        ctx.pillSelector = ctx.elementSelector;
        ctx.fullSelector = ctx.elementSelector = `.${params.handles}`;

        // Force the handles to stay in place
        ctx.followCursor = false;
    },
    onDragStart({ ctx, addStyle, getRect }) {
        const parent = ctx.current.element.closest(ctx.pillSelector);
        const pRect = getRect(ctx.current.pill);

        addStyle(ctx.current.pill, {
            position: "fixed !important",
            left: `${ctx.current.initialPillRect.x}px`,
            top: `${pRect.y}px`,
            width: `${pRect.width}px`,
            height: `${pRect.height}px`,
            zIndex: 1000,
        });
        return { pill: parent };
    },
    onDrag({ ctx, addStyle }) {
        const { current, pointer, pillSelector, rtl } = ctx;
        const closestStep = closest(pointer.x, current.steps);
        const { x, width } = current.initialPillRect;

        if (closestStep === current.lastStep) {
            return;
        }
        current.lastStep = closestStep;

        addStyle(current.element, { position: "absolute !important" });

        const isLeftHandle = rtl ? !current.isStart : current.isStart;
        if (isLeftHandle) {
            addStyle(current.pill, {
                left: `${closestStep}px`,
                width: `${x + width - closestStep}px`,
            });
        } else {
            addStyle(current.pill, {
                left: `${x}px`,
                width: `${closestStep - x + current.elementRect.width}px`,
            });
        }

        const grabbedHandle = isLeftHandle ? "left" : "right";
        const parentPill = current.element.closest(pillSelector);
        const diff =
            current.steps.indexOf(closestStep) - current.steps.indexOf(current.initialStep);

        return { pill: parentPill, grabbedHandle, diff };
    },
    onDragEnd({ ctx }) {
        const { current, pillSelector } = ctx;
        const parentPill = current.element.closest(pillSelector);
        return { pill: parentPill };
    },
    onDrop({ ctx }) {
        const { current, pointer, pillSelector } = ctx;
        const parentPill = current.element.closest(pillSelector);
        const closestStep = closest(pointer.x, current.steps);

        if (closestStep === current.initialStep) {
            return;
        }

        const direction = current.isStart ? "start" : "end";
        let diff = current.steps.indexOf(closestStep) - current.steps.indexOf(current.initialStep);
        if (current.isStart) {
            diff *= -1;
        }

        return { pill: parentPill, diff, direction };
    },
    onWillStartDrag({ ctx, addStyle, getRect }) {
        const { cellSelector, current, pointer, pillSelector, precision, rtl } = ctx;

        ctx.cursor = getComputedStyle(current.element).cursor;
        current.pill = current.element.closest(pillSelector);

        const pRect = getRect(current.pill);
        const handleRect = getRect(current.element);
        const { x: px, width: pw } = pRect;

        current.isStart = current.element.classList.contains(HANDLE_CLASS_START);
        current.steps = [];

        const isLeftHandle = rtl ? !current.isStart : current.isStart;
        let step;
        for (const cell of current.container.querySelectorAll(cellSelector)) {
            const cRect = getRect(cell);
            const posX = Math.floor(
                isLeftHandle ? cRect.x : cRect.x + cRect.width - handleRect.width
            );
            step ||= cRect.width / precision;
            for (let i = 0; i < precision; i++) {
                const stepOffset = step * i;
                const x = isLeftHandle ? posX + stepOffset : posX - stepOffset;
                if (
                    !current.steps.includes(x) &&
                    ((isLeftHandle && x <= px + pw - step) || (!isLeftHandle && px <= x))
                ) {
                    current.steps.push(x);
                }
            }
        }

        current.steps.sort((a, b) => (isLeftHandle ? b - a : a - b));

        current.initialPillRect = pRect;
        current.initialStep = closest(pointer.x, current.steps);

        addStyle(ctx.ref.el, { pointerEvents: "auto" });
    },
});
