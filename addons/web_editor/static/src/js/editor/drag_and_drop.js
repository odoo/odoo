/** @odoo-module **/
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { pick } from "@web/core/utils/objects";
import { reactive } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { closest, touching } from "@web/core/utils/ui";
import { clamp } from "@web/core/utils/numbers";
import * as gridUtils from "@web_editor/js/common/grid_layout_utils";

/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableHandlerParams} DraggableHandlerParams */
/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableBuilderParams} DraggableBuilderParams */
/** @typedef {import("@web/core/utils/draggable").DraggableParams} DraggableParams */

/** @typedef {DraggableHandlerParams & { dropzone: HTMLElement | null, helper: HTMLElement }} DragAndDropHandlerParams */
/** @typedef {DraggableHandlerParams & { helper: HTMLElement }} DragAndDropStartParams */
/** @typedef {DraggableHandlerParams & { dropzone: HTMLElement }} DropzoneHandlerParams */
/**
 * @typedef DragAndDropParams
 * @extends {DraggableParams}
 *
 * MANDATORY
 * @property {(() => Array)} dropzones a function that returns the available dropzones
 * @property {(() => HTMLElement)} helper a function that returns a helper element
 * that will follow the cursor when dragging
 * @property {HTMLElement || (() => HTMLElement)} scrollingElement the element on
 * which a scroll should be triggered
 *
 * HANDLERS (Optional)
 * @property {(params: DragAndDropStartParams) => any} [onDragStart]
 * called when a dragging sequence is initiated
 * @property {(params: DropzoneHandlerParams) => any} [dropzoneOver]
 * called when an element is over a dropzone
 * @property {(params: DropzoneHandlerParams) => any} [dropzoneOut]
 * called when an element is leaving a dropzone
 * @property {(params: DragAndDropHandlerParams) => any} [onDrag]
 * called when an element is being dragged
 * @property {(params: DragAndDropHandlerParams) => any} [onDragEnd]
 * called when the dragging sequence is over
 */
/**
 * @typedef NativeDraggableState
 * @property {(params: DraggableParams) => any} update
 * method to update the params of the draggable
 * @property {import("@web/core/utils/draggable").DraggableState} state
 * state of the draggable component
 * @property {() => any} destroy
 * method to destroy and unbind the draggable component
 */
/**
 * Utility function to create a native draggable component
 *
 * @param {DraggableBuilderParams} hookParams
 * @param {DraggableParams} initialParams
 * @returns {NativeDraggableState}
 */
export function useNativeDraggable(hookParams, initialParams) {
    const setupFunctions = new Map();
    const cleanupFunctions = [];
    const currentParams = { ...initialParams };
    const setupHooks = {
        wrapState: reactive,
        throttle: throttleForAnimation,
        addListener: (el, type, callback, options) => {
            el.addEventListener(type, callback, options);
            cleanupFunctions.push(() => el.removeEventListener(type, callback));
        },
        setup: (setupFn, depsFn) => setupFunctions.set(setupFn, depsFn),
        teardown: (cleanupFn) => {
            cleanupFunctions.push(cleanupFn);
        }
    };
    // Compatibility for tests
    const el = initialParams.ref.el;
    // TODO this is probably to be removed in master: the received params
    // contain the selector that should be checked and it will be transferred
    // to the makeDraggableHook function. There should not be any need to add
    // the default selector class here.
    el.classList.add("o_draggable");
    cleanupFunctions.push(() => el.classList.remove("o_draggable"));

    const draggableState = makeDraggableHook({ setupHooks, ...hookParams})(currentParams);
    draggableState.enable = true;
    const draggableComponent = {
        state: draggableState,
        update: (newParams) => {
            Object.assign(currentParams, newParams);
            setupFunctions.forEach((depsFn, setupFn) => setupFn(...depsFn()));
        },
        destroy: () => {
            cleanupFunctions.forEach((cleanupFn) => cleanupFn());
        }
    };
    draggableComponent.update({});
    return draggableComponent;
}

function updateElementPosition(el, { x, y }, styleFn, offset = { x: 0, y: 0 }) {
    return styleFn(el, { top: `${y - offset.y}px`, left: `${x - offset.x}px`});
}
/** @type DraggableBuilderParams */
const dragAndDropHookParams = {
    name: "useDragAndDrop",
    acceptedParams: {
        dropzones: [Function],
        scrollingElement: [Object, Function],
        helper: [Function],
        extraWindow: [Object, Function],
    },
    edgeScrolling: { enabled: true },
    onComputeParams({ ctx, params }) {
        // The helper is mandatory and will follow the cursor instead
        ctx.followCursor = false;
        ctx.scrollingElement = params.scrollingElement;
        ctx.getHelper = params.helper;
        ctx.getDropZones = params.dropzones;
    },
    onWillStartDrag: ({ ctx }) => {
        ctx.current.container = ctx.scrollingElement;
        ctx.current.helperOffset = { x: 0, y: 0 };
    },
    onDragStart: ({ ctx, addStyle, addCleanup, addClass }) => {
        // Use the helper as the tracking element to properly update scroll values.
        ctx.current.element = ctx.getHelper({ ...ctx.current, ...ctx.pointer });
        ctx.current.helper = ctx.current.element;
        ctx.current.helper.style.position = "fixed";
        // We want the pointer events on the helper so that the cursor
        // is properly displayed.
        ctx.current.helper.classList.remove("o_dragged");
        ctx.current.helper.style.cursor = ctx.cursor;
        ctx.current.helper.style.pointerEvents = "auto";

        // If the helper is inside the iframe, we want pointer events on the
        // frame element so that they reach the window and properly apply
        // the cursor.
        const frameElement = ctx.current.helper.ownerDocument.defaultView.frameElement;
        if (frameElement) {
            addClass(frameElement, "pe-auto");
        }

        addCleanup(() => ctx.current.helper.remove());

        updateElementPosition(ctx.current.helper, ctx.pointer, addStyle, ctx.current.helperOffset);

        return pick(ctx.current, "element", "helper");
    },
    onDrag: ({ ctx, addStyle, callHandler }) => {
        ctx.current.helper.classList.add("o_draggable_dragging");

        updateElementPosition(ctx.current.helper, ctx.pointer, addStyle, ctx.current.helperOffset);
        // Unfortunately, DOMRect is not an Object, so spreading operator from
        // `touching` does not work, so convert DOMRect to plain object.
        let helperRect = ctx.current.helper.getBoundingClientRect();
        helperRect = {
            x: helperRect.x,
            y: helperRect.y,
            width: helperRect.width,
            height: helperRect.height,
        };
        const dropzoneEl = closest(touching(ctx.getDropZones(), helperRect), helperRect);
        // Update the drop zone if it's in grid mode
        if (ctx.current.dropzone?.el && ctx.current.dropzone.el.classList.contains("oe_grid_zone")) {
            ctx.current.dropzone.rect = ctx.current.dropzone.el.getBoundingClientRect();
        }
        if (
            ctx.current.dropzone &&
            (
                ctx.current.dropzone.el === dropzoneEl
                || (
                    !dropzoneEl
                    && touching([ctx.current.helper], ctx.current.dropzone.rect).length > 0
                )
            )
        ) {
            // If no new dropzone but old one is still valid, return early.
            return pick(ctx.current, "element", "dropzone", "helper");
        }

        if (ctx.current.dropzone && dropzoneEl !== ctx.current.dropzone.el) {
            callHandler("dropzoneOut", { dropzone: ctx.current.dropzone });
            delete ctx.current.dropzone;
        }

        if (dropzoneEl) {
            // Save rect information prior to calling the over function
            // to keep a consistent dropzone even if content was added.
            const rect = DOMRect.fromRect(dropzoneEl.getBoundingClientRect());
            ctx.current.dropzone = {
                el: dropzoneEl,
                rect: {
                    x: rect.x, y: rect.y, width: rect.width, height: rect.height
                }
            };
            callHandler("dropzoneOver", { dropzone: ctx.current.dropzone });
        }
        return pick(ctx.current, "element", "dropzone", "helper");
    },
    onDragEnd({ ctx }) {
        return pick(ctx.current, "element", "dropzone", "helper");
    }
};
/**
 * Function to start a drag and drop handler
 *
 * @param {DragAndDropParams} initialParams params given to the drag and drop
 * component
 * @returns {NativeDraggableState}
 */
export function useDragAndDrop(initialParams) {
    return useNativeDraggable(dragAndDropHookParams, initialParams);
}
export class dragAndDropHelper {
    constructor(odooEditor, draggedItemEl, bodyEl, observerName) {
        this.dragState = {};
        this.draggedItemEl = draggedItemEl;
        this.odooEditor = odooEditor;
        this.bodyEl = bodyEl;
        this.observerName = observerName;
        this.isOriginalSnippet = !!draggedItemEl.dataset.snippet;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Removes the background grid and updates the dragged item style and
     * property according to the dropzone on which it was dropped.
     */
    dragAndDropStopGrid() {
        const rowEl = this.draggedItemEl.parentNode;
        if (rowEl && rowEl.classList.contains("o_grid_mode")) {
            // Case when dropping the column in a grid

            // Disable dragMove handler
            this.dragState.gridMode = false;

            // Defining the column grid area with its position
            const gridProp = gridUtils._getGridProperties(rowEl);

            const style = window.getComputedStyle(this.draggedItemEl);
            const top = parseFloat(style.top);
            const left = parseFloat(style.left);

            const rowStart = Math.round(top / (gridProp.rowSize + gridProp.rowGap)) + 1;
            const columnStart = Math.round(left / (gridProp.columnSize + gridProp.columnGap)) + 1;
            const rowEnd = rowStart + this.dragState.columnRowCount;
            const columnEnd = columnStart + this.dragState.columnColCount;

            this.draggedItemEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowEnd} / ${columnEnd}`;

            gridUtils._gridCleanUp(rowEl, this.draggedItemEl);
            this._removeDragHelper(rowEl);
        } else if (this.draggedItemEl.classList.contains("o_grid_item") && this.isDropped()) {
            // Case when dropping a grid item in a non-grid dropzone
            this.odooEditor.observerActive(this.observerName);
            gridUtils._convertToNormalColumn(this.draggedItemEl);
            this.odooEditor.observerUnactive(this.observerName);
        }
    }
    /**
     * Places the item on dropzoneEl and updates the dragged item style and
     * property according to the dropzoneEl characteristics.
     *
     * @param {HTMLElement} dropzoneEl - The closest dropzone near which the
     * dragged item was dropped.
     */
    droppedNear(dropzoneEl) {
        if (dropzoneEl.classList.contains("oe_grid_zone")) {
            // Case when a column is dropped near a grid
            const rowEl = dropzoneEl.parentNode;

            this._handleGridItemCreation(dropzoneEl);

            // Placing it in the top left corner
            this.odooEditor.observerActive(this.observerName);
            this.draggedItemEl.style.gridArea = `1 / 1 / ${1 + this.dragState.columnRowCount} / ${1 + this.dragState.columnColCount}`;
            const rowCount = Math.max(rowEl.dataset.rowCount, this.dragState.columnRowCount);
            rowEl.dataset.rowCount = rowCount;
            this.odooEditor.observerUnactive(this.observerName);

            // Setting the grid item z-index
            if (rowEl === this.dragState.startingGrid) {
                this.draggedItemEl.style.zIndex = this.dragState.startingZIndex;
            } else {
                gridUtils._setElementToMaxZindex(this.draggedItemEl, rowEl);
            }
        } else if (this.draggedItemEl.classList.contains("o_grid_item")) {
            // Case when a grid column is dropped near a non-grid dropzone
            this.odooEditor.observerActive(this.observerName);
            gridUtils._convertToNormalColumn(this.draggedItemEl);
            this.odooEditor.observerUnactive(this.observerName);
        }
        this.dragState.currentDropzoneEl = dropzoneEl;
    }
    /**
     * Handles the insertion of an element in a dropzone.
     *
     * @param {HTMLElement} dropzoneEl - The dropzone over which the element is
     * dragged.
     */
    dropzoneOver(dropzoneEl) {
        dropzoneEl.after(this.draggedItemEl);
        dropzoneEl.classList.add("invisible");

        this.dragState.currentDropzoneEl = dropzoneEl;

        if (dropzoneEl.classList.contains("oe_grid_zone")) {
            // Case where the column we are dragging is over a grid dropzone
            const rowEl = dropzoneEl.parentNode;

            this._handleGridItemCreation(dropzoneEl);
            const columnColCount = this.dragState.columnColCount;
            const columnRowCount = this.dragState.columnRowCount;

            // Creating the drag helper
            const dragHelperEl = document.createElement("div");
            dragHelperEl.classList.add("o_we_drag_helper");
            dragHelperEl.style.gridArea = `1 / 1 / ${1 + columnRowCount} / ${1 + columnColCount}`;
            rowEl.append(dragHelperEl);

            // Updating the dropzone (in the case where the column over the
            // dropzone is bigger than the grid).
            const backgroundGridEl = rowEl.querySelector(".o_we_background_grid");
            const rowCount = Math.max(rowEl.dataset.rowCount, columnRowCount);
            dropzoneEl.style.gridRowEnd = rowCount + 1;

            this.odooEditor.observerActive(this.observerName);
            // Setting the moving grid item, the background grid and the drag
            // helper z-indexes. The grid item z-index is set to its original
            // one if we are in its starting grid, or to the maximum z-index of
            // the grid otherwise.
            if (rowEl === this.dragState.startingGrid) {
                this.draggedItemEl.style.zIndex = this.dragState.startingZIndex;
            } else {
                gridUtils._setElementToMaxZindex(this.draggedItemEl, rowEl);
            }
            gridUtils._setElementToMaxZindex(backgroundGridEl, rowEl);
            gridUtils._setElementToMaxZindex(dragHelperEl, rowEl);

            // Setting the column height and width to keep its size when the
            // grid-area is removed (as it prevents it from moving with the
            // mouse).
            const gridProp = gridUtils._getGridProperties(rowEl);
            const columnHeight = columnRowCount * (gridProp.rowSize + gridProp.rowGap) - gridProp.rowGap;
            const columnWidth = columnColCount * (gridProp.columnSize + gridProp.columnGap) - gridProp.columnGap;
            this.draggedItemEl.style.height = columnHeight + "px";
            this.draggedItemEl.style.width = columnWidth + "px";
            this.draggedItemEl.style.position = "absolute";
            this.draggedItemEl.style.removeProperty("grid-area");
            rowEl.style.position = "relative";
            this.odooEditor.observerUnactive(this.observerName);

            // Storing useful information
            this.dragState.startingHeight = rowEl.clientHeight;
            this.dragState.currentHeight = rowEl.clientHeight;
            this.dragState.dragHelperEl = dragHelperEl;
            this.dragState.backgroundGridEl = backgroundGridEl;
            this.dragState.gridMode = true;
        }
    }
    /**
     * Handles the extraction of an element from a dropzone.
     *
     * @param {HTMLElement} dropzoneEl - The dropzone that the element leaves
     * with its position and dimension information.
     */
    dropzoneOut(dropzoneEl) {
        const rowEl = dropzoneEl.parentNode;
        this.draggedItemEl.remove();
        if (rowEl.classList.contains("o_grid_mode")) {
            // Cleaning
            this.dragState.gridMode = false;
            gridUtils._gridCleanUp(rowEl, this.draggedItemEl);
            this.draggedItemEl.style.removeProperty("z-index");
            this._removeDragHelper(rowEl);
            // Resize the current grid dropzone and its associated background
            // grid.
            const rowCount = parseInt(rowEl.dataset.rowCount);
            const gridRowEnd = Math.max(rowCount + 1, 1);
            dropzoneEl.style.gridRowEnd = gridRowEnd;
            this.dragState.backgroundGridEl.style.gridRowEnd = gridRowEnd;
            if (this.isOriginalSnippet && !!this.draggedItemEl.firstElementChild?.dataset.snippet) {
                // Unwrap the dragged element from its column ('div') if it is a
                // wrapped snippet and if the drag and drop originally applied
                // on the snippet itself.
                this.draggedItemEl = this.draggedItemEl.firstElementChild;
            }
        } else {
            // Show the dropzone if it is not a grid
            dropzoneEl.classList.remove("invisible");
        }
        delete this.dragState.currentDropzoneEl;
    }
    /**
     * Removes the siblings/children that would add a dropzone as direct child
     * of a grid area and make a dedicated set out of the identified grid areas.
     *
     * @param {jQuery} $selectorSiblings - Elements that must have siblings drop
     * zones.
     * @param {jQuery} $selectorChildren - Elements that must have child drop
     * zones between each of existing child.
     * @return {Object} Elements that are in grid mode and for which a grid
     * dropzone needs to be inserted.
     */
    filterOutSelectorsGrids($selectorSiblings, $selectorChildren) {
        const selectorGrids = new Set();
        const filterOutSelectorGrids = ($selectorItems, getDropzoneParent) => {
            if (!$selectorItems) {
                return;
            }
            // Looping backwards because elements are removed, so the indexes
            // are not lost.
            for (let i = $selectorItems.length - 1; i >= 0; i--) {
                const el = getDropzoneParent($selectorItems[i]);
                if (el.classList.contains("o_grid_mode")) {
                    $selectorItems.splice(i, 1);
                    selectorGrids.add(el);
                }
            }
        };
        filterOutSelectorGrids($selectorSiblings, (el) => el.parentElement);
        filterOutSelectorGrids($selectorChildren, (el) => el);
        return selectorGrids;
    }
    /**
     * Returns an element horizontal and vertical margins and borders.
     *
     * @param {HTMLElement} draggedItemEl - The element whose margins and
     * borders are required.
     * @returns {Object} The element horizontal and vertical margins and
     * borders.
     */
    getDraggedElementBordersAndMargins(draggedItemEl = this.draggedItemEl) {
        const style = window.getComputedStyle(draggedItemEl);
        const borderX = parseFloat(style.borderLeft) + parseFloat(style.borderRight);
        const marginX = parseFloat(style.marginLeft) + parseFloat(style.marginRight);
        const borderY = parseFloat(style.borderTop) + parseFloat(style.borderBottom);
        const marginY = parseFloat(style.marginTop) + parseFloat(style.marginBottom);
        return { borderX: borderX, marginX: marginX, borderY: borderY, marginY: marginY };
    }
    /**
     * Checks if we are currently over a dropzone, that is, if
     * `currentDropzoneEl` is defined.
     *
     * @returns {Boolean}
     */
    isDropped() {
        return !!this.dragState.currentDropzoneEl;
    }
    /**
     * Places a column in a grid on mouse move.
     *
     * @param {Integer} x - The x position of the mouse.
     * @param {Integer} y - The y position of the mouse.
     */
    onDragMove(x, y) {
        if (!this.dragState.gridMode || !this.dragState.currentDropzoneEl) {
            return;
        }
        const columnEl = this.draggedItemEl;
        const rowEl = columnEl.parentNode;

        // Computing the rowEl position
        const rowElTop = rowEl.getBoundingClientRect().top;
        const rowElLeft = rowEl.getBoundingClientRect().left;

        // Getting the column dimensions
        const borderWidth = parseFloat(window.getComputedStyle(columnEl).borderWidth);
        const columnHeight = columnEl.clientHeight + 2 * borderWidth;
        const columnWidth = columnEl.clientWidth + 2 * borderWidth;

        // Placing the column where the mouse is
        let top = y - rowElTop - this.dragState.mousePositionYOnElement;
        const bottom = top + columnHeight;
        let left = x - rowElLeft - this.dragState.mousePositionXOnElement;

        // Horizontal & vertical overflow
        left = clamp(left, 0, rowEl.clientWidth - columnWidth);
        top = top < 0 ? 0 : top;

        columnEl.style.top = top + "px";
        columnEl.style.left = left + "px";

        // Computing the drag helper corresponding grid area
        const gridProp = gridUtils._getGridProperties(rowEl);

        const rowStart = Math.round(top / (gridProp.rowSize + gridProp.rowGap)) + 1;
        const columnStart = Math.round(left / (gridProp.columnSize + gridProp.columnGap)) + 1;
        const rowEnd = rowStart + this.dragState.columnRowCount;
        const columnEnd = columnStart + this.dragState.columnColCount;

        const dragHelperEl = this.dragState.dragHelperEl;
        if (parseInt(dragHelperEl.style.gridRowStart) !== rowStart) {
            dragHelperEl.style.gridRowStart = rowStart;
            dragHelperEl.style.gridRowEnd = rowEnd;
        }

        if (parseInt(dragHelperEl.style.gridColumnStart) !== columnStart) {
            dragHelperEl.style.gridColumnStart = columnStart;
            dragHelperEl.style.gridColumnEnd = columnEnd;
        }

        // Vertical overflow/underflow.
        // Updating the reference heights, the dropzone and the background grid.
        const startingHeight = this.dragState.startingHeight;
        const currentHeight = this.dragState.currentHeight;
        const backgroundGridEl = this.dragState.backgroundGridEl;
        const dropzoneEl = this.dragState.currentDropzoneEl;
        const rowOverflow = Math.round((bottom - currentHeight) / (gridProp.rowSize + gridProp.rowGap));
        const updateRows = bottom > currentHeight || (bottom <= currentHeight && bottom > startingHeight);
        const rowCount = Math.max(rowEl.dataset.rowCount, this.dragState.columnRowCount);
        const maxRowEnd = rowCount + gridUtils.additionalRowLimit + 1;
        if (Math.abs(rowOverflow) >= 1 && updateRows) {
            if (rowEnd <= maxRowEnd) {
                const dropzoneEnd = parseInt(dropzoneEl.style.gridRowEnd);
                dropzoneEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
                backgroundGridEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
                this.dragState.currentHeight += rowOverflow * (gridProp.rowSize + gridProp.rowGap);
            } else {
                // Don't add new rows if we have reached the limit
                dropzoneEl.style.gridRowEnd = maxRowEnd;
                backgroundGridEl.style.gridRowEnd = maxRowEnd;
                this.dragState.currentHeight = (maxRowEnd - 1) * (gridProp.rowSize + gridProp.rowGap) - gridProp.rowGap;
            }
        }
    }
    /**
     * Changes some behaviors before the drag and drop.
     *
     * @private
     * @returns {Function} a function that restores what was changed when the
     *  drag and drop is over.
     */
    prepareDrag() {
        return () => {};
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Transforms the dragged item into a grid element if it is not one already.
     * If the dragged element is a snippet, it is wrapped into a div to create a
     * column.
     *
     * @private
     * @param {HTMLElement} dropzoneEl - The grid dropzone where the dragged
     * item is placed.
     */
    _handleGridItemCreation(dropzoneEl) {
        const rowEl = dropzoneEl.parentNode;
        if (this.draggedItemEl.dataset.snippet) {
            // Wrap the dragged element into a column ('div') if it is a snippet
            this.draggedItemEl.remove();
            const columnEl = document.createElement("div");
            columnEl.prepend(this.draggedItemEl);
            this.draggedItemEl = columnEl;
            dropzoneEl.after(this.draggedItemEl);
        }
        if (!this.draggedItemEl.classList.contains("o_grid_item")) {
            // Converting the column to grid
            this.odooEditor.observerActive(this.observerName);
            const spans = gridUtils._convertColumnToGrid(
                rowEl,
                this.draggedItemEl,
                this.dragState.columnWidth,
                this.dragState.columnHeight
            );
            this.odooEditor.observerUnactive(this.observerName);

            // Storing the column spans
            this.dragState.columnColCount = spans.columnColCount;
            this.dragState.columnRowCount = spans.columnRowCount;
        }
    }
    /**
     * Removes the drag helper and resizes the grid.
     *
     * @private
     * @param {HTMLElement} rowEl - The row in grid mode.
     */
    _removeDragHelper(rowEl) {
        this.dragState.dragHelperEl.remove();
        this.odooEditor.observerActive(this.observerName);
        gridUtils._resizeGrid(rowEl);
        this.odooEditor.observerUnactive(this.observerName);
    }
}
