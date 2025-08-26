import { useComponent, useEffect, useRef } from "@odoo/owl";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { shallowEqual } from "@web/core/utils/objects";
import { closest } from "@web/core/utils/ui";
import { useCallbackRecorder } from "@web/search/action_hook";

const CELL_SELECTOR = `.fc-day:not(.fc-col-header-cell)`;
const ROW_SELECTOR = `tr[role="row"]`;
const EVENT_CONTAINER_SELECTOR = ".fc-daygrid-event-harness";
const IGNORE_SELECTOR = [".fc-event", ".fc-more-cell", ".fc-more-popover"].join(",");

function getClosestCell(ctx) {
    const { pointer, ref } = ctx;
    return closest(ref.el.querySelectorAll(CELL_SELECTOR), pointer);
}

function getElementIndex(element) {
    return [].indexOf.call(element?.parentNode.children || [], element);
}

function getCoordinates(cell) {
    const colIndex = getElementIndex(cell);
    const rowIndex = getElementIndex(cell.closest(ROW_SELECTOR));
    return { colIndex, rowIndex };
}

function getBlockBounds({ initCoord, coord }) {
    const [startColIndex, endColIndex] = [initCoord.colIndex, coord.colIndex].sort();
    const [startRowIndex, endRowIndex] = [initCoord.rowIndex, coord.rowIndex].sort();
    return { startColIndex, endColIndex, startRowIndex, endRowIndex };
}

function getResult(ctx) {
    const { current, ref } = ctx;
    const { startColIndex, endColIndex, startRowIndex, endRowIndex } = getBlockBounds(current);
    const selectorParts = [];
    for (let x = startColIndex; x <= endColIndex; x++) {
        for (let y = startRowIndex; y <= endRowIndex; y++) {
            selectorParts.push(
                `tbody tr[role="row"]:nth-child(${y + 1}) > .fc-day:nth-child(${x + 1})`
            );
        }
    }
    const selector = selectorParts.join(",");
    return { selectedCells: [...ref.el.querySelectorAll(selector)].filter(ctx.cellIsSelectable) };
}

// @ts-ignore
const useBlockSelection = makeDraggableHook({
    name: "useBlockSelection",
    acceptedParams: {
        cellIsSelectable: [Function],
    },
    onComputeParams({ ctx, params }) {
        ctx.followCursor = false;
        ctx.cellIsSelectable = params.cellIsSelectable;
    },
    onWillStartDrag({ addClass, ctx }) {
        const { current, ref } = ctx;
        addClass(ref.el, "pe-auto");
        const cell = getClosestCell(ctx);
        addClass(cell, "pe-auto");
        const coord = getCoordinates(cell);
        current.initCoord = coord;
        current.coord = coord;
        return getResult(ctx);
    },
    onDragStart({ ctx }) {
        return getResult(ctx);
    },
    onDrag({ ctx }) {
        const { current } = ctx;
        const cell = getClosestCell(ctx);
        const coord = getCoordinates(cell);
        if (shallowEqual(current.coord, coord)) {
            return;
        }
        current.coord = coord;
        return getResult(ctx);
    },
    onDrop({ ctx }) {
        return getResult(ctx);
    },
});

export function useSquareSelection(params = {}) {
    const cellIsSelectable = params.cellIsSelectable || (() => true);
    const component = useComponent();
    const ref = useRef("fullCalendar");
    const highlightClass = "o-highlight";

    const removeHighlight = () => {
        ref.el.querySelectorAll(`.${highlightClass}`).forEach((node) => {
            node.classList.remove(highlightClass);
        });
    };
    const highlight = ({ selectedCells }) => {
        removeHighlight();
        selectedCells.forEach((node) => {
            node.classList.add(highlightClass);
        });
    };

    useCallbackRecorder(component.props.callbackRecorder, removeHighlight);
    const selectState = useBlockSelection({
        enable: () => component.props.model.hasMultiCreate,
        ignore: EVENT_CONTAINER_SELECTOR,
        elements: CELL_SELECTOR,
        ref,
        edgeScrolling: { speed: 40, threshold: 150 },
        cellIsSelectable,
        onWillStartDrag: removeHighlight,
        onDragStart: highlight,
        onDrag: highlight,
        onDrop: ({ selectedCells }) => {
            highlight({ selectedCells });
            component.props.onSquareSelection(selectedCells);
        },
    });

    const onClick = (ev) => {
        if (selectState.dragging) {
            return;
        }
        const ignoreElement = ev.target.closest(IGNORE_SELECTOR);
        if (ignoreElement) {
            return;
        }
        const eventContainer = ev.target.closest(EVENT_CONTAINER_SELECTOR);
        if (eventContainer) {
            return;
        }
        const cell = ev.target.closest(CELL_SELECTOR);
        if (!cell) {
            return;
        }
        const coord = getCoordinates(cell);
        const current = { initCoord: coord, coord };
        const { selectedCells } = getResult({ current, ref, cellIsSelectable });
        highlight({ selectedCells });
        component.props.onSquareSelection(selectedCells);
    };

    useEffect(
        (el, hasMultiCreate) => {
            if (!hasMultiCreate) {
                return;
            }
            el && el.addEventListener("click", onClick);
            return () => {
                el && el.removeEventListener("click", onClick);
            };
        },
        () => [ref.el, component.props.model.hasMultiCreate]
    );
}
