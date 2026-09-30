import { useComponent, useEffect, useExternalListener, useRef } from "@odoo/owl";
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
    const [startColIndex, endColIndex] = [initCoord.colIndex, coord.colIndex].sort((a, b) => a - b);
    const [startRowIndex, endRowIndex] = [initCoord.rowIndex, coord.rowIndex].sort((a, b) => a - b);
    return { startColIndex, endColIndex, startRowIndex, endRowIndex };
}

function getSelectedCellsInBlock(ctx) {
    const { cellIsSelectable, current, ref } = ctx;
    const { startColIndex, endColIndex, startRowIndex, endRowIndex } = getBlockBounds(current);
    const selectedCells = [];
    for (const cell of ref.el.querySelectorAll(`tbody tr[role="row"] .fc-day`)) {
        const { colIndex, rowIndex } = getCoordinates(cell);
        if (
            startColIndex <= colIndex &&
            colIndex <= endColIndex &&
            startRowIndex <= rowIndex &&
            rowIndex <= endRowIndex &&
            cellIsSelectable(cell)
        ) {
            selectedCells.push(cell);
        }
    }
    return { selectedCells };
}

function getSelectedCellsBetween2Cells(ctx, prevCell, cellClicked) {
    const { cellIsSelectable, ref } = ctx;
    const cells = [...ref.el.querySelectorAll(`tbody tr[role="row"] .fc-day`)];
    const index1 = cells.indexOf(prevCell);
    if (index1 === -1) {
        return new Set([cellClicked]);
    }
    const index2 = cells.indexOf(cellClicked);
    const [startIndex, endIndex] = [index1, index2].sort((a, b) => a - b);
    return new Set(cells.slice(startIndex, endIndex + 1).filter((cell) => cellIsSelectable(cell)));
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
        return getSelectedCellsInBlock(ctx);
    },
    onDragStart({ ctx }) {
        return getSelectedCellsInBlock(ctx);
    },
    onDrag({ ctx }) {
        const { current } = ctx;
        const cell = getClosestCell(ctx);
        const coord = getCoordinates(cell);
        if (shallowEqual(current.coord, coord)) {
            return;
        }
        current.coord = coord;
        return getSelectedCellsInBlock(ctx);
    },
    onDrop({ ctx }) {
        return getSelectedCellsInBlock(ctx);
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

    let allSelectedCells = new Set();
    const getAllCells = (cells, action) => {
        cells = new Set(cells);
        switch (action) {
            case "add":
                return allSelectedCells.union(cells);
            case "toggle":
                return allSelectedCells.symmetricDifference(cells);
            case "replace":
                return cells;
        }
    };

    const highlight = ({ selectedCells }) => {
        removeHighlight();
        selectedCells.forEach((node) => {
            node.classList.add(highlightClass);
        });
    };

    useCallbackRecorder(component.props.callbackRecorder, () => {
        allSelectedCells = new Set();
        prevSelectedCell = null;
        removeHighlight();
    });

    let action = null;
    let prevSelectedCell = null;
    const update = ({ selectedCells }) => {
        const allSelectedCells = getAllCells(selectedCells, action);
        highlight({ selectedCells: allSelectedCells });
    };

    const selectState = useBlockSelection({
        enable: () => component.props.model.hasMultiCreate,
        ignore: EVENT_CONTAINER_SELECTOR,
        elements: CELL_SELECTOR,
        ref,
        edgeScrolling: { speed: 40, threshold: 150 },
        cellIsSelectable,
        onDragStart: ({ selectedCells }) => {
            prevSelectedCell = null;
            action = ctrlPressed ? "add" : "replace";
            update({ selectedCells });
        },
        onDrag: update,
        onDrop: ({ selectedCells }) => {
            allSelectedCells = getAllCells(selectedCells, action);
            action = null;
            highlight({ selectedCells: allSelectedCells });
            component.props.onSquareSelection([...allSelectedCells]);
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
        const pseudoCtx = { current, ref, cellIsSelectable };
        const { selectedCells } = getSelectedCellsInBlock(pseudoCtx);
        const selectedCell = selectedCells[0];
        if (prevSelectedCell && shiftPressed) {
            allSelectedCells = getSelectedCellsBetween2Cells(
                pseudoCtx,
                prevSelectedCell,
                selectedCell
            );
        } else {
            const action = ctrlPressed ? "toggle" : "replace";
            allSelectedCells = getAllCells(selectedCells, action);
        }
        if (!prevSelectedCell || !shiftPressed) {
            prevSelectedCell = selectedCell;
        }
        highlight({ selectedCells: allSelectedCells });
        component.props.onSquareSelection([...allSelectedCells]);
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

    let ctrlPressed = false;
    let shiftPressed = false;
    function onWindowKeyDown(ev) {
        if (ev.key === "Control") {
            ctrlPressed = true;
        } else if (ev.key === "Shift") {
            shiftPressed = true;
        }
    }

    function onWindowKeyUp(ev) {
        if (ev.key === "Control") {
            ctrlPressed = false;
        } else if (ev.key === "Shift") {
            shiftPressed = false;
        }
    }

    useExternalListener(window, "keydown", onWindowKeyDown);
    useExternalListener(window, "keyup", onWindowKeyUp);
}
