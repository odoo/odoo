import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { clamp } from "@web/core/utils/numbers";
import {
    addBackgroundGrid,
    additionalRowLimit,
    checkIfImageColumn,
    cleanUpGrid,
    convertColumnToGrid,
    convertToNormalColumn,
    getGridItemProperties,
    getGridProperties,
    resizeGrid,
    setElementToMaxZindex,
    toggleGridMode,
} from "@html_builder/utils/grid_layout_utils";
import { isElement } from "@html_editor/utils/dom_info";

const gridItemSelector = ".row.o_grid_mode > div.o_grid_item";

function isGridItem(el) {
    return el.matches(gridItemSelector);
}

export class GridLayoutPlugin extends Plugin {
    static id = "gridLayout";
    static dependencies = ["selection", "builderOptions"];
    resources = {
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        on_cloned_handlers: this.onCloned.bind(this),
        on_removed_handlers: this.onRemoved.bind(this),
        // Drag and drop from sidebar
        on_snippet_dragged_handlers: this.onSnippetDragged.bind(this),
        on_snippet_over_dropzone_handlers: this.onSnippetOverDropzone.bind(this),
        on_snippet_move_handlers: this.onSnippetMove.bind(this),
        on_snippet_out_dropzone_handlers: this.onSnippetOutDropzone.bind(this),
        on_snippet_dropped_over_handlers: this.onSnippetDroppedOver.bind(this),
        on_snippet_dropped_near_handlers: this.onSnippetDroppedNear.bind(this),
        on_snippet_dropped_handlers: withSequence(1000, this.onSnippetDropped.bind(this)),
        // Drag and drop from the page
        is_draggable_handlers: this.isDraggable.bind(this),
        on_element_dragged_handlers: this.onElementDragged.bind(this),
        on_element_over_dropzone_handlers: this.onDropzoneOver.bind(this),
        on_element_move_handlers: this.onDragMove.bind(this),
        on_element_out_dropzone_handlers: this.onDropzoneOut.bind(this),
        on_element_dropped_over_handlers: this.onElementDroppedOver.bind(this),
        on_element_dropped_near_handlers: this.onElementDroppedNear.bind(this),
        on_element_dropped_handlers: this.onElementDropped.bind(this),
        // Ignore background grid in history
        savable_mutation_record_predicates: this.ignoreBackgroundGrid.bind(this),
    };

    setup() {
        this.overlayTarget = null;
        this.isRtl = this.config.isEditableRTL;
        this.iframe = this.document.defaultView.frameElement;
    }

    /**
     * Checks if the given container element has the grid mode option.
     *
     * @param {HTMLElement} containerEl the container element
     * @returns {Boolean}
     */
    hasGridLayoutOption(containerEl) {
        // Check if the "LayoutOption" option is active.
        const { targetEl } = this.dependencies.builderOptions.findOption(
            containerEl,
            "LayoutOption",
            true
        );
        return !!targetEl && targetEl === containerEl;
    }

    ignoreBackgroundGrid(record) {
        if (record.type === "childList") {
            const addedOrRemovedNode = (record.addedTrees[0] || record.removedTrees[0]).node;
            // Do not record the addition/removal of the background grid.
            if (
                isElement(addedOrRemovedNode) &&
                addedOrRemovedNode.matches(".o_we_background_grid")
            ) {
                return false;
            }
        }
        return true;
    }

    getActiveOverlayButtons(target) {
        if (!isGridItem(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        if (!this.config.isMobileView(this.overlayTarget)) {
            buttons.push(
                {
                    class: "o_send_back oi",
                    title: _t("Send to back"),
                    handler: this.sendGridItemToBack.bind(this),
                },
                {
                    class: "o_bring_front oi",
                    title: _t("Bring to front"),
                    handler: this.bringGridItemToFront.bind(this),
                }
            );
        }
        return buttons;
    }

    onCloned({ cloneEl }) {
        if (isGridItem(cloneEl)) {
            // If it is a grid item, shift the clone by one cell to the right
            // and to the bottom, wrap to the first column if we reached the
            // last one.
            let { rowStart, rowEnd, columnStart, columnEnd } = getGridItemProperties(cloneEl);
            const columnSpan = columnEnd - columnStart;
            columnStart = columnEnd === 13 ? 1 : columnStart + 1;
            columnEnd = columnStart + columnSpan;
            const newGridArea = `${rowStart + 1} / ${columnStart} / ${rowEnd + 1} / ${columnEnd}`;
            cloneEl.style.gridArea = newGridArea;

            // Update the z-index and the grid row count.
            const rowEl = cloneEl.parentElement;
            setElementToMaxZindex(cloneEl, rowEl);
            resizeGrid(rowEl);
        }
    }

    onRemoved({ nextTargetEl }) {
        // Resize the grid, if any, to have the correct row count.
        // If the active element after a removal is a grid item, it means we
        // potentially removed a sibling grid item.
        if (nextTargetEl.classList.contains("o_grid_item")) {
            resizeGrid(nextTargetEl.parentElement);
        }
    }

    /**
     * Puts the grid item behind all the others (minimum z-index).
     */
    sendGridItemToBack() {
        const rowEl = this.overlayTarget.parentNode;
        const columnEls = [...rowEl.children].filter((el) => el !== this.overlayTarget);
        const minZindex = Math.min(...columnEls.map((el) => el.style.zIndex));

        // While the minimum z-index is not 0, it is OK to decrease it and to
        // set the column to it. Otherwise, the column is set to 0 and the
        // other columns z-index are increased by one.
        if (minZindex > 0) {
            this.overlayTarget.style.zIndex = minZindex - 1;
        } else {
            columnEls.forEach((columnEl) => columnEl.style.zIndex++);
            this.overlayTarget.style.zIndex = 0;
        }
    }

    /**
     * Puts the grid item in front all the others (maximum z-index).
     */
    bringGridItemToFront() {
        const rowEl = this.overlayTarget.parentNode;
        setElementToMaxZindex(this.overlayTarget, rowEl);
    }

    /**
     * Adapts the height of the grid item (if any) to its content and returns a
     * function restoring the grid item height.
     *
     * @param {HTMLElement} el the new content
     * @param {Boolean} [shouldResizeGrid=true] `true` if the grid height should also
     *   be adapted.
     * @returns {Function} a function restoring the grid item state
     */
    adjustGridItem(el, shouldResizeGrid = true) {
        const gridItemEl = el.closest(".o_grid_item");
        if (gridItemEl && gridItemEl !== el && !this.config.isMobileView(gridItemEl)) {
            const rowEl = gridItemEl.parentElement;
            const { rowGap, rowSize } = getGridProperties(rowEl);
            const { rowStart, rowEnd } = getGridItemProperties(gridItemEl);
            const oldRowSpan = rowEnd - rowStart;

            // Compute the new height.
            const { borderTop, borderBottom, paddingTop, paddingBottom } =
                window.getComputedStyle(gridItemEl);
            const borderY = parseFloat(borderTop) + parseFloat(borderBottom);
            const paddingY = parseFloat(paddingTop) + parseFloat(paddingBottom);
            const height = gridItemEl.scrollHeight + borderY + paddingY;

            const rowSpan = Math.ceil((height + rowGap) / (rowSize + rowGap));
            gridItemEl.style.gridRowEnd = rowStart + rowSpan;
            gridItemEl.classList.remove(`g-height-${oldRowSpan}`);
            gridItemEl.classList.add(`g-height-${rowSpan}`);
            if (shouldResizeGrid) {
                resizeGrid(rowEl);
            }

            return () => {
                // Restore the grid item height.
                gridItemEl.style.gridRowEnd = rowEnd;
                gridItemEl.classList.remove(`g-height-${rowSpan}`);
                gridItemEl.classList.add(`g-height-${oldRowSpan}`);
                if (shouldResizeGrid) {
                    resizeGrid(rowEl);
                }
            };
        }

        return () => {};
    }

    //--------------------------------------------------------------------------
    // DRAG AND DROP HANDLERS (from the sidebar)
    //--------------------------------------------------------------------------

    /**
     * Returns the grid dropzone that overlaps with the given dropzone, if any.
     *
     * @param {HTMLElement} dropzoneEl the dropzone
     * @returns {HTMLElement}
     */
    getOverlappingGridDropzone(dropzoneEl) {
        const closestGridEl = dropzoneEl.closest(".o_grid_mode");
        const gridDropzoneEl = closestGridEl && closestGridEl.querySelector(".oe_grid_zone");
        return gridDropzoneEl;
    }

    /**
     * Wraps the given element inside a grid item, makes the drag and drop use
     * this item instead and returns it.
     *
     * @param {HTMLElement} el the element
     * @param {HTMLElement} dropzoneEl the grid dropzone
     * @param {Object} dragState the current drag state
     * @returns {HTMLElement}
     */
    wrapInGridItem(el, dropzoneEl, dragState) {
        // Create the grid item.
        const columnEl = document.createElement("div");
        const columnSpan = dragState.snippet.gridColumnSpan || 6;
        columnEl.classList.add(
            "o_grid_item",
            `col-lg-${columnSpan}`,
            `g-col-lg-${columnSpan}`,
            "g-height-1"
        );
        columnEl.style.gridArea = `1 / 1 / 2 / ${columnSpan + 1}`;
        dropzoneEl.after(columnEl);
        columnEl.append(el);
        dragState.draggedEl = columnEl;

        // Remove the padding/margins.
        const { paddingToRemove, marginToRemove, marginToAdd } = dragState;
        el.classList.remove(...paddingToRemove, ...marginToRemove);
        el.classList.add(...marginToAdd);

        // Adjust the grid item dimensions to its content and store them.
        this.adjustGridItem(el, false);
        const { rowStart, rowEnd } = getGridItemProperties(columnEl);
        dragState.columnSpan = columnSpan;
        dragState.rowSpan = rowEnd - rowStart;
        return columnEl;
    }

    /**
     * Called when we start dragging the snippet.
     *
     * @param {Object} - snippetEl: the dragged snippet
     *                 - dragState: the current drag state
     */
    onSnippetDragged({ snippetEl, dragState }) {
        // Store the padding and margin classes to remove/add them when needed.
        const paddingRegex = /^((pt|pb)\d{1,3}$)/;
        const marginRegex = /^((mt|my)-\d$)/;
        const paddingClasses = [...snippetEl.classList].filter((c) => paddingRegex.test(c));
        const marginClasses = [...snippetEl.classList].filter((c) => marginRegex.test(c));
        Object.assign(dragState, {
            paddingToRemove: paddingClasses,
            marginToRemove: marginClasses,
        });

        // Check if CSS rules are potentially applying a top margin.
        snippetEl.classList.remove(...paddingClasses, ...marginClasses);
        this.document.body.appendChild(snippetEl);
        const { marginTop } = getComputedStyle(snippetEl);
        dragState.marginToAdd = parseInt(marginTop) ? ["mt-0"] : [];
        snippetEl.remove();
        snippetEl.classList.add(...paddingClasses, ...paddingClasses);
    }

    /**
     * Called when the snippet is dragged over a dropzone.
     *
     * @param {Object}
     */
    onSnippetOverDropzone({ snippetEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            // If we are not over a grid dropzone, hide the grid dropzone that
            // is overlapping with it (if any).
            const gridDropzoneEl = this.getOverlappingGridDropzone(dropzoneEl);
            if (gridDropzoneEl) {
                gridDropzoneEl.classList.add("invisible");
            }
        } else {
            // If we are over a grid dropzone, wrap the snippet inside a column and
            // drag that column instead.
            const columnEl = this.wrapInGridItem(snippetEl, dropzoneEl, dragState);
            // Drag the column by the middle top.
            const iframeRect = this.iframe.getBoundingClientRect();
            dragState.mousePositionYOnElement = 0;
            dragState.mousePositionXOnElement =
                (iframeRect.x + columnEl.scrollWidth / 2) * (this.isRtl ? -1 : 1);
        }

        this.onDropzoneOver({ draggedEl: dragState.draggedEl, dragState });
    }

    /**
     * Called when the snippet is dragged out of a dropzone.
     *
     * @param {Object}
     */
    onSnippetOutDropzone({ snippetEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        this.onDropzoneOut({ draggedEl: dragState.draggedEl, dragState });

        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            // If we were not over a grid dropzone, show back the hidden grid
            // dropzone if any.
            const gridDropzoneEl = this.getOverlappingGridDropzone(dropzoneEl);
            if (gridDropzoneEl) {
                gridDropzoneEl.classList.remove("invisible");
            }
        } else {
            // If we were over a grid dropzone, unwrap the snippet.
            dropzoneEl.after(snippetEl);
            dragState.draggedEl.remove();
            dragState.draggedEl = snippetEl;
            // Restore the padding/margins.
            const { paddingToRemove, marginToRemove, marginToAdd } = dragState;
            snippetEl.classList.add(...paddingToRemove, ...marginToRemove);
            snippetEl.classList.remove(...marginToAdd);
        }
    }

    /**
     * Called while moving the dragged element over a dropzone.
     *
     * @param {Object} - dragState: the current drag state.
     *                 - x, y: the horizontal/vertical position of the helper
     */
    onSnippetMove({ dragState, x, y }) {
        if (!dragState.overGrid) {
            return;
        }
        this.onDragMove({ draggedEl: dragState.draggedEl, dragState, x, y });
    }

    /**
     * Called when the snippet is dropped when over a dropzone.
     *
     * @param {Object} - droppedEl: the dropped element
     *                 - dragState: the current drag state
     */
    onSnippetDroppedOver({ droppedEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            return;
        }
        this.onElementDroppedOver({ droppedEl, dragState });
    }

    /**
     * Called when the snippet is dropped near a dropzone.
     *
     * @param {Object} - dropzoneEl: the closest dropzone
     */
    onSnippetDroppedNear({ droppedEl, dropzoneEl, dragState }) {
        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            return;
        }
        // If we are near a grid dropzone, wrap the snippet inside a column.
        this.wrapInGridItem(droppedEl, dropzoneEl, dragState);
        this.onElementDroppedNear({ droppedEl: dragState.draggedEl, dropzoneEl, dragState });
    }

    /**
     * Called when the snippet is dropped in general.
     *
     * @param {Object}
     */
    onSnippetDropped({ snippetEl, dragState }) {
        // Readjust the closest grid item (needed to compute its height without
        // the inner dropzones).
        if ("restoreGridItem" in dragState) {
            dragState.restoreGridItem();
            this.adjustGridItem(snippetEl);
        }
    }

    //--------------------------------------------------------------------------
    // DRAG AND DROP HANDLERS (from the page)
    //--------------------------------------------------------------------------

    /**
     * Tells if the given element is draggable.
     *
     * @param {HTMLElement} targetEl the element
     * @returns {Boolean}
     */
    isDraggable(targetEl) {
        // The columns move handles are not visible in mobile view to prevent
        // dragging them.
        const isColumn = targetEl.parentElement?.classList.contains("row");
        if (isColumn && this.config.isMobileView(targetEl)) {
            return false;
        }
        return true;
    }

    /**
     * Called when we start dragging an element.
     *
     * @param {Object} - draggedEl: the dragged element
     *                 - dragState: the current drag state
     */
    onElementDragged({ draggedEl, dragState }) {
        const parentEl = draggedEl.parentElement;
        const isColumn = parentEl.classList.contains("row");
        if (isColumn) {
            const rowEl = parentEl;
            const containerEl = rowEl.parentElement;
            const columnEl = draggedEl;

            // Allow the grid mode if the container has the option or if
            // the grid mode is already activated.
            const hasGridOption = this.hasGridLayoutOption(containerEl);
            const isRowInGridMode = rowEl.classList.contains("o_grid_mode");
            const allowGridMode = hasGridOption || isRowInGridMode;

            if (allowGridMode) {
                // Toggle the grid mode if it is not already on.
                if (!isRowInGridMode) {
                    const preserveSelection = this.dependencies.selection.preserveSelection;
                    toggleGridMode(containerEl, preserveSelection, this.config.mobileBreakpoint);
                }
                const gridItemProps = getGridItemProperties(columnEl);

                // Store the grid column and row spans of the column.
                const { columnStart, columnEnd, rowStart, rowEnd } = gridItemProps;
                dragState.columnSpan = columnEnd - columnStart;
                dragState.rowSpan = rowEnd - rowStart;

                // Store the initial state of the column.
                const { gridArea, zIndex } = gridItemProps;
                dragState.startGridArea = gridArea;
                dragState.startZindex = zIndex;
                dragState.startGridEl = rowEl;
            } else {
                // If the column comes from a snippet that does not toggle the
                // grid mode on drag, store its width and height to use them
                // when the column goes over a grid dropzone.
                const style = window.getComputedStyle(columnEl);
                const { borderLeft, borderRight, borderTop, borderBottom } = style;
                const borderX = parseFloat(borderLeft) + parseFloat(borderRight);
                const borderY = parseFloat(borderTop) + parseFloat(borderBottom);
                // Use the image dimension if the column only contains an image.
                const isImageColumn = checkIfImageColumn(columnEl);
                const sizedEl = isImageColumn ? columnEl.querySelector("img") : columnEl;
                dragState.columnWidth = sizedEl.scrollWidth + borderX;
                dragState.columnHeight = sizedEl.scrollHeight + borderY;
            }
        }
    }

    /**
     * Called when the element is dragged over a dropzone.
     *
     * @param {Object}
     */
    onDropzoneOver({ draggedEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            // Adjust the closest grid item if any.
            dragState.restoreGridItem = this.adjustGridItem(draggedEl);
            return;
        }

        const rowEl = dropzoneEl.parentElement;
        const columnEl = draggedEl;
        // If the column does not come from a grid mode snippet, convert it to a
        // grid item and store its dimensions.
        if (!columnEl.classList.contains("o_grid_item")) {
            const { columnWidth, columnHeight } = dragState;
            const spans = convertColumnToGrid(
                rowEl,
                columnEl,
                columnWidth,
                columnHeight,
                this.config.mobileBreakpoint
            );
            dragState.columnSpan = spans.columnSpan;
            dragState.rowSpan = spans.rowSpan;
        }
        const { columnSpan, rowSpan } = dragState;

        // Create the drag helper.
        const dragHelperEl = document.createElement("div");
        dragHelperEl.classList.add("o_we_drag_helper");
        dragHelperEl.style.gridArea = `1 / 1 / ${1 + rowSpan} / ${1 + columnSpan}`;
        rowEl.append(dragHelperEl);

        // Add the background grid and update the dropzone (in the case where
        // the column is bigger than the grid).
        const backgroundGridEl = addBackgroundGrid(rowEl, rowSpan);
        const rowCount = Math.max(rowEl.dataset.rowCount, rowSpan);
        dropzoneEl.style.gridRowEnd = rowCount + 1;

        // Set the column, the background grid and the drag helper z-indexes.
        // The grid item z-index is set to its original one if we are in its
        // starting grid, or to the maximum z-index of the grid otherwise.
        const { startGridEl, startZindex } = dragState;
        if (rowEl === startGridEl) {
            columnEl.style.zIndex = startZindex;
        } else {
            setElementToMaxZindex(columnEl, rowEl);
        }
        setElementToMaxZindex(backgroundGridEl, rowEl);
        setElementToMaxZindex(dragHelperEl, rowEl);

        // Force the column height and width to keep its size when the grid-area
        // will be removed (as it prevents it from moving with the mouse).
        const { rowGap, rowSize, columnGap, columnSize } = getGridProperties(rowEl);
        const columnHeight = rowSpan * (rowSize + rowGap) - rowGap;
        const columnWidth = columnSpan * (columnSize + columnGap) - columnGap;
        Object.assign(columnEl.style, {
            height: `${columnHeight}px`,
            width: `${columnWidth}px`,
            position: "absolute",
            gridArea: "",
        });
        rowEl.style.position = "relative";

        // Store information needed to drag over the grid.
        Object.assign(dragState, {
            startHeight: rowEl.clientHeight,
            currentHeight: rowEl.clientHeight,
            dragHelperEl,
            backgroundGridEl,
            overGrid: true,
        });
    }

    /**
     * Called when the element is dragged out of a dropzone.
     *
     * @param {Object}
     */
    onDropzoneOut({ draggedEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        if (!dropzoneEl.classList.contains("oe_grid_zone")) {
            // Restore the adjusted grid item (if any).
            if ("restoreGridItem" in dragState) {
                dragState.restoreGridItem();
                delete dragState.restoreGridItem;
            }
            return;
        }

        dragState.overGrid = false;
        // Clean the grid and the column.
        const columnEl = draggedEl;
        const rowEl = dropzoneEl.parentElement;
        const { dragHelperEl, backgroundGridEl } = dragState;
        cleanUpGrid(rowEl, columnEl, dragHelperEl, backgroundGridEl);
        columnEl.style.removeProperty("z-index");

        // Resize the grid and the dropzone.
        resizeGrid(rowEl);
        const rowCount = parseInt(rowEl.dataset.rowCount);
        dropzoneEl.style.gridRowEnd = Math.max(rowCount + 1, 1);
    }

    /**
     * Called when the element is dropped when over a dropzone.
     *
     * @param {Object} - droppedEl: the dropped element
     *                 - dragState: the current drag state
     */
    onElementDroppedOver({ droppedEl, dragState }) {
        const dropzoneEl = dragState.currentDropzoneEl;
        const columnEl = droppedEl;
        if (dropzoneEl.classList.contains("oe_grid_zone")) {
            dragState.overGrid = false;
            const rowEl = dropzoneEl.parentElement;
            const { dragHelperEl, backgroundGridEl } = dragState;

            // Place the column at the same grid-area as the drag helper.
            columnEl.style.gridArea = dragHelperEl.style.gridArea;

            // Clean the grid and the column and resize the grid.
            cleanUpGrid(rowEl, columnEl, dragHelperEl, backgroundGridEl);
            resizeGrid(rowEl);
        } else if (columnEl.classList.contains("o_grid_item")) {
            // Case when dropping a grid item in a non-grid dropzone.
            convertToNormalColumn(columnEl, this.config.mobileBreakpoint);
        }
    }

    /**
     * Called when the element is dropped near a dropzone.
     *
     * @param {Object} - droppedEl: the dropped element
     *                 - dropzoneEl: the closest dropzone
     *                 - dragState: the current drag state
     */
    onElementDroppedNear({ droppedEl, dropzoneEl, dragState }) {
        const columnEl = droppedEl;
        if (dropzoneEl.classList.contains("oe_grid_zone")) {
            const rowEl = dropzoneEl.parentElement;
            // If the column does not come from a grid mode snippet, convert it to a
            // grid item and store its dimensions.
            if (!columnEl.classList.contains("o_grid_item")) {
                const { columnWidth, columnHeight } = dragState;
                const spans = convertColumnToGrid(
                    rowEl,
                    columnEl,
                    columnWidth,
                    columnHeight,
                    this.config.mobileBreakpoint
                );
                dragState.columnSpan = spans.columnSpan;
                dragState.rowSpan = spans.rowSpan;
            }
            const { columnSpan, rowSpan } = dragState;

            // Place the column in the top left corner, set its z-index and
            // resize the grid.
            columnEl.style.gridArea = `1 / 1 / ${1 + rowSpan} / ${1 + columnSpan}`;
            const { startGridEl, startZindex } = dragState;
            if (rowEl === startGridEl) {
                columnEl.style.zIndex = startZindex;
            } else {
                setElementToMaxZindex(columnEl, rowEl);
            }
            resizeGrid(rowEl);
        } else if (columnEl.classList.contains("o_grid_item")) {
            // Case when a grid item is dropped near a non-grid dropzone.
            convertToNormalColumn(columnEl, this.config.mobileBreakpoint);
        }
    }

    /**
     * Called while moving the dragged element over a dropzone.
     *
     * @param {Object} - droppedEl: the dropped element
     *                 - dragState: the current drag state.
     *                 - x, y: the horizontal/vertical position of the helper
     */
    onDragMove({ draggedEl, dragState, x, y }) {
        if (!dragState.overGrid) {
            return;
        }

        // Get the column dimensions and the grid position.
        const columnEl = draggedEl;
        const columnHeight = parseFloat(columnEl.style.height);
        const columnWidth = parseFloat(columnEl.style.width);

        const rowEl = columnEl.parentElement;
        const rowRect = rowEl.getBoundingClientRect();
        const rowTop = rowRect.top;
        const rowLeft = rowRect.left;
        const rowRight = rowRect.right;

        // Place the column where the mouse is, without overflowing horizontally
        // or above the top of the grid.
        const { mousePositionYOnElement, mousePositionXOnElement } = dragState;
        let top = y - rowTop - mousePositionYOnElement;

        let left;
        if (this.isRtl) {
            left = rowRight - x - mousePositionXOnElement - columnWidth;
        } else {
            left = x - rowLeft - mousePositionXOnElement;
        }

        top = top < 0 ? 0 : top;
        left = clamp(left, 0, rowEl.clientWidth - columnWidth);
        const bottom = top + columnHeight;
        columnEl.style.top = `${top}px`;
        if (this.isRtl) {
            columnEl.style.right = `${left}px`;
        } else {
            columnEl.style.left = `${left}px`;
        }

        // Compute the drag helper grid-area corresponding to the column
        // position.
        const { rowGap, rowSize, columnGap, columnSize } = getGridProperties(rowEl);
        const { columnSpan, rowSpan, dragHelperEl } = dragState;

        const rowStart = Math.round(top / (rowSize + rowGap)) + 1;
        const columnStart = Math.round(left / (columnSize + columnGap)) + 1;
        const rowEnd = rowStart + rowSpan;
        const columnEnd = columnStart + columnSpan;
        dragHelperEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowEnd} / ${columnEnd}`;

        // Update the reference heights, the dropzone and the background grid,
        // depending on the vertical overflow/underflow.
        const dropzoneEl = dragState.currentDropzoneEl;
        const { startHeight, currentHeight, backgroundGridEl } = dragState;

        const rowOverflow = Math.round((bottom - currentHeight) / (rowSize + rowGap));
        const shouldUpdateRows =
            bottom > currentHeight || (bottom <= currentHeight && bottom > startHeight);
        const rowCount = Math.max(rowEl.dataset.rowCount, rowSpan);
        const maxRowEnd = rowCount + additionalRowLimit + 1;
        if (Math.abs(rowOverflow) >= 1 && shouldUpdateRows) {
            if (rowEnd <= maxRowEnd) {
                const newGridEnd = parseInt(dropzoneEl.style.gridRowEnd) + rowOverflow;
                dropzoneEl.style.gridRowEnd = newGridEnd;
                backgroundGridEl.style.gridRowEnd = newGridEnd;
                dragState.currentHeight += rowOverflow * (rowSize + rowGap);
            } else {
                // Do not add new rows if we have reached the limit.
                dropzoneEl.style.gridRowEnd = maxRowEnd;
                backgroundGridEl.style.gridRowEnd = maxRowEnd;
                dragState.currentHeight = (maxRowEnd - 1) * (rowSize + rowGap) - rowGap;
            }
        }
    }

    /**
     * Called when the element is dropped in general.
     *
     * @param {Object}
     */
    onElementDropped({ droppedEl, dragState }) {
        // Resize the grid from where the column came from (if any), as it may
        // have not been resized if the column did not go over it.
        const { startGridEl } = dragState;
        if (startGridEl) {
            resizeGrid(startGridEl);
        }

        // Adjust the closest grid item if any.
        if ("restoreGridItem" in dragState) {
            dragState.restoreGridItem();
        }
        this.adjustGridItem(droppedEl);

        // The position of a grid item did not change if it is in its original
        // grid and if it still has the same grid-area.
        if (droppedEl.classList.contains("o_grid_item")) {
            dragState.hasSamePositionAsStart = () => {
                const parentEl = droppedEl.parentElement;
                const gridArea = droppedEl.style.gridArea;
                const { startGridEl, startGridArea } = dragState;
                return parentEl === startGridEl && gridArea === startGridArea;
            };
        }
    }
}
