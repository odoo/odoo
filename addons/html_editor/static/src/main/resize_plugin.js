import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getElementHoveredEdge } from "@html_editor/utils/perspective_utils";

export class ResizePlugin extends Plugin {
    static id = "resize";
    static dependencies = ["history"];

    setup() {
        // Set up mouse event listeners for resize interactions.
        this.addDomListener(this.editable, "mousemove", this.onMouseMove);
        this.addDomListener(this.editable, "mousedown", this.onMouseDown);
        this.addDomListener(this.editable, "mouseleave", this.onMouseLeave);

        // Load resizing parameters from plugin resources.
        this.resizingParameters = this.getResource("resizing_parameters");

        // Tracks last highlighted resizable element & associated hover class.
        this.lastHoveredResizableElement = null;

        // Precompute selectors and store them inside each parameters.
        for (const resizingParameter of this.resizingParameters) {
            // Scoped selector for resizable elements.
            resizingParameter._containerScopedSelector = resizingParameter.resizableElementsSelector
                .split(",")
                .map((sel) => resizingParameter.parentContainerSelector + " " + sel.trim())
                .join(", ");

            // Precompute selectors for items without inline width/height.
            const resizableSelectors = resizingParameter.resizableElementsSelector
                .split(",")
                .map((sel) => sel.trim());

            resizingParameter._unsizedItemsSelector = {
                width: resizableSelectors.map((sel) => `${sel}:not([style*="width"])`).join(", "),
                height: resizableSelectors.map((sel) => `${sel}:not([style*="height"])`).join(", "),
            };
        }
    }

    /**
     * Remove hover CSS classes from previously highlighted resizable elements.
     *
     * @param {void}
     * @returns {void}
     */
    removeResizeHoverClasses() {
        if (!this.lastHoveredResizableElement) {
            return;
        }
        this.lastHoveredResizableElement.resizableElement.classList.remove(
            this.lastHoveredResizableElement.hoverClass
        );
        this.lastHoveredResizableElement = null;
    }

    /**
     * Update the cursor style to indicate resize direction.
     *
     * @param {'col'|'row'|false} direction - resize direction/false to reset
     * @returns {void}
     */
    updateResizeCursor(direction) {
        const classList = this.editable.classList;
        // Remove previous resize cursor classes.
        classList.remove("o_col_resize", "o_row_resize");

        // Apply appropriate cursor based on resize direction.
        if (direction === "col") {
            classList.add("o_col_resize");
        } else if (direction === "row") {
            classList.add("o_row_resize");
        }
    }

    /**
     * Handle mouse down events to initiate resize operations.
     *
     * @param {MouseEvent} ev - The mouse down event
     * @returns {void}
     */
    onMouseDown(ev) {
        // Start resize if hovering a resizable element edge.
        if (!this.activeHover) {
            return;
        }

        const { resizableElement, resizingParameter, resizeEdge, direction } = this.activeHover;
        ev.preventDefault();

        const previousSibling = resizableElement.previousElementSibling;
        const nextSibling = resizableElement.nextElementSibling;

        let target1, target2;

        if (resizeEdge === "left" || resizeEdge === "top") {
            target1 = previousSibling;
            target2 = resizableElement;
        } else if (resizeEdge === "right" || resizeEdge === "bottom") {
            target1 = resizableElement;
            target2 = nextSibling;
        }
        if (direction === "col" && this.config.direction === "rtl") {
            // Swap targets for RTL column resizing.
            [target1, target2] = [target2, target1];
        }

        // Apply target resolver (e.g., first-row cell for table columns).
        if (resizingParameter.targetResolver) {
            target1 = resizingParameter.targetResolver(target1);
            target2 = resizingParameter.targetResolver(target2);
        }

        this.isResizingElement = true;
        const handleResize = (ev) =>
            this.handleResize(ev, direction, resizingParameter, target1, target2);
        const endResizeOperation = (ev) => {
            ev.preventDefault();
            this.isResizingElement = false;
            this.updateResizeCursor(false);
            this.dependencies.history.addStep();
            this.document.removeEventListener("mousemove", handleResize);
            this.document.removeEventListener("mouseup", endResizeOperation);
            this.document.removeEventListener("mouseleave", endResizeOperation);
        };

        // Set up global event listeners for resize operation.
        this.document.addEventListener("mousemove", handleResize);
        this.document.addEventListener("mouseup", endResizeOperation);
        this.document.addEventListener("mouseleave", endResizeOperation);
    }

    /**
     * Handle mouse move events to detect hover over resizable element edges.
     *
     * @param {MouseEvent} ev - The mouse move event
     * @returns {void}
     */
    onMouseMove(ev) {
        // Ignore mouse movements during an active resize or when the mouse
        // is still over the same element.
        if (this.isResizingElement) {
            return;
        }

        // Reset active hover state and clear any existing hover classes.
        this.activeHover = null;
        this.removeResizeHoverClasses();

        // Find first resizing parameters matching the hovered node and store
        // the relevant active hover metadata.
        for (const resizingParameter of this.resizingParameters) {
            const resizableElement = closestElement(
                ev.target,
                resizingParameter._containerScopedSelector
            );
            if (!resizableElement) {
                continue;
            }

            // Apply hover visual.
            if (resizingParameter.hoverClass) {
                this.lastHoveredResizableElement = {
                    resizableElement,
                    hoverClass: resizingParameter.hoverClass,
                };
                resizableElement.classList.add(resizingParameter.hoverClass);
            }

            // Determine which edge of the element is being hovered for resizing.
            const resizeEdge = getElementHoveredEdge(ev, resizableElement);
            if (resizeEdge && resizingParameter.allowedEdges.includes(resizeEdge)) {
                // Store active hover information for potential resize operation.
                this.activeHover = {
                    resizableElement,
                    resizingParameter,
                    resizeEdge,
                    direction: resizeEdge === "left" || resizeEdge === "right" ? "col" : "row",
                };
                break;
            }
        }
        // Update cursor to indicate resize based on hover direction.
        this.updateResizeCursor(this.activeHover?.direction || false);
    }

    /**
     * Clears any active resize hover state (hover highlight + resize cursor)
     * so resize handle doesn't remain visible when pointer exits the editor.
     *
     * @returns {void}
     */
    onMouseLeave() {
        if (this.isResizingElement) {
            return;
        }
        this.activeHover = null;
        this.removeResizeHoverClasses();
        this.updateResizeCursor(false);
    }

    /**
     * Handle the actual resize operation during mouse movement.
     *
     * @param {MouseEvent} ev - The mouse move event during resize
     * @param {'col'|'row'} direction - The resize direction
     * @param {Object} resizingParameter - The resizing parameter object
     * @param {HTMLElement} target1 - The first resize target element
     * @param {HTMLElement} target2 - The second resize target element
     * @returns {void}
     */
    handleResize(ev, direction, resizingParameter, target1, target2) {
        ev.preventDefault();
        // Determine resize position: first, middle, or last element.
        const position = target1 ? (target2 ? "middle" : "last") : "first";
        let [item, neighbor] = [target1 || target2, target2];

        // Find the container element that holds the resizable items
        const resizeContainer = closestElement(item, resizingParameter.parentContainerSelector);
        const [sizeProp, positionProp, clientPositionProp] =
            direction === "col" ? ["width", "x", "clientX"] : ["height", "y", "clientY"];
        const isRTL = this.config.direction === "rtl";

        // Width operations: preserve container width to maintain layout.
        if (sizeProp === "width") {
            const resizeContainerRect = resizeContainer.getBoundingClientRect();
            resizeContainer.style[sizeProp] = Math.round(resizeContainerRect[sizeProp]) + "px";
        }

        // Find elements without explicit size styling and set their current
        // computed size.
        for (const unsizedItem of resizeContainer.querySelectorAll(
            resizingParameter._unsizedItemsSelector[sizeProp]
        )) {
            unsizedItem.style[sizeProp] =
                Math.round(unsizedItem.getBoundingClientRect()[sizeProp]) + "px";
        }

        // RTL adjustment: swap elements for consistent resize logic.
        if (direction === "col" && isRTL && position === "middle") {
            [item, neighbor] = [neighbor, item];
        }

        const minSize = resizingParameter.minSize;

        switch (position) {
            case "first": {
                // Resizing the first element (may affect container margins).
                const marginProp =
                    direction === "col" ? (isRTL ? "marginRight" : "marginLeft") : "marginTop";
                const itemRect = item.getBoundingClientRect();
                const parentStyle = getComputedStyle(resizeContainer);
                const currentMargin = parseFloat(parentStyle[marginProp]) || 0;
                let sizeDelta = itemRect[positionProp] - ev[clientPositionProp];
                if (direction === "col" && isRTL) {
                    // RTL adjustment: reverse the delta calculation.
                    sizeDelta =
                        ev[clientPositionProp] - itemRect[positionProp] - itemRect[sizeProp];
                }

                const newMargin = Math.round(currentMargin - sizeDelta);
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;
                if (newMargin >= 0 && newSize > minSize) {
                    const resizeContainerRect = resizeContainer.getBoundingClientRect();
                    // Update container margin and element size.
                    resizeContainer.style.cssText += ` ${marginProp
                        .replace(/([A-Z])/g, "-$1")
                        .toLowerCase()}: ${newMargin}px !important;`;
                    item.style[sizeProp] = Math.round(newSize) + "px";

                    // Adjust container width for column resizing to maintain
                    // total size.
                    if (sizeProp === "width") {
                        resizeContainer.style[sizeProp] =
                            Math.round(resizeContainerRect[sizeProp] + sizeDelta) + "px";
                    }
                }
                break;
            }
            case "middle": {
                // Resizing middle element (affects both item and neighbor).
                const [itemRect, neighborRect] = [
                    item.getBoundingClientRect(),
                    neighbor.getBoundingClientRect(),
                ];

                const currentSize = itemRect[sizeProp];
                const newSize = ev[clientPositionProp] - itemRect[positionProp];

                const editableStyle = getComputedStyle(this.editable);
                const sizeDelta = newSize - currentSize;
                const currentNeighborSize = neighborRect[sizeProp];
                const newNeighborSize = currentNeighborSize - sizeDelta;

                const maxWidth =
                    this.editable.clientWidth -
                    parseFloat(editableStyle.paddingLeft) -
                    parseFloat(editableStyle.paddingRight);
                const resizeContainerRect = resizeContainer.getBoundingClientRect();

                if (
                    newSize > minSize &&
                    // Allow resizing if:
                    // - this is a row resize (rows don't shrink the neighbor),
                    // - OR the neighbor would stay above its minimum size,
                    // - OR the container would fit inside editable area.
                    (direction === "row" ||
                        newNeighborSize > minSize ||
                        resizeContainerRect[sizeProp] + sizeDelta < maxWidth)
                ) {
                    item.style[sizeProp] = Math.round(newSize) + "px";

                    if (direction === "col") {
                        // For columns, adjust neighbor size or maintain
                        // current if below minimum.
                        neighbor.style[sizeProp] =
                            Math.round(
                                newNeighborSize > minSize ? newNeighborSize : currentNeighborSize
                            ) + "px";
                    }
                }
                break;
            }
            case "last": {
                // Resizing the last element in container.
                const itemRect = item.getBoundingClientRect();
                let sizeDelta =
                    ev[clientPositionProp] - (itemRect[positionProp] + itemRect[sizeProp]);
                if (direction === "col" && isRTL) {
                    // RTL adjustment for last element.
                    sizeDelta = itemRect[positionProp] - ev[clientPositionProp];
                }
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;

                if ((newSize >= 0 || direction === "row") && newSize > minSize) {
                    const resizeContainerRect = resizeContainer.getBoundingClientRect();
                    if (sizeProp === "width") {
                        // Adjust container width to adapt element size change.
                        resizeContainer.style[sizeProp] =
                            Math.round(resizeContainerRect[sizeProp] + sizeDelta) + "px";
                    }
                    item.style[sizeProp] = Math.round(newSize) + "px";
                }
                break;
            }
        }
    }
}
