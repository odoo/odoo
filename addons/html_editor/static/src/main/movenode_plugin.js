import { useNativeDraggable } from "@html_editor/utils/drag_and_drop";
import { endPos } from "@html_editor/utils/position";
import { Plugin } from "../plugin";
import { ancestors, closestElement } from "../utils/dom_traversal";

const WIDGET_CONTAINER_WIDTH = 25;
const WIDGET_MOVE_SIZE = 20;

const ALLOWED_ELEMENTS =
    "h1, h2, h3, p, hr, pre, blockquote, ul, ol, table, [data-embedded], .o_text_columns, .o_editor_banner, .oe_movable";

export class MoveNodePlugin extends Plugin {
    static name = "movenode";
    static dependencies = ["selection", "position", "local-overlay"];
    resources = {
        layoutGeometryChange: () => {
            if (this.currentMovableElement) {
                this.setMovableElement(this.currentMovableElement);
            }
            this.updateHooks();
        },
    };

    setup() {
        this.intersectionObserver = new IntersectionObserver(
            this.intersectionObserverCallback.bind(this),
            {
                root: document,
            }
        );
        this.visibleMovableElements = new Set();

        this.elementHookMap = new Map();

        this.addDomListener(this.editable, "mousemove", this.onMousemove, true);
        this.addDomListener(this.editable, "touchmove", this.onMousemove, true);
        this.addDomListener(this.document, "keydown", this.onDocumentKeydown, true);
        this.addDomListener(this.document, "mousemove", this.onDocumentMousemove, true);
        this.addDomListener(this.document, "touchmove", this.onDocumentMousemove, true);

        // This container help to add zone into which the mouse can activate the move widget.
        this.widgetHookContainer = this.shared.makeLocalOverlay("oe-widget-hooks-container");
        // This container contains the differents widgets.
        this.widgetContainer = this.shared.makeLocalOverlay("oe-widgets-container");
        // This container contains the jquery helper element.
        this.dragHelperContainer = this.shared.makeLocalOverlay("oe-movenode-helper-container");
        // This container contains drop zones. They are the zones that handle where the drop should happen.
        this.dropzonesContainer = this.shared.makeLocalOverlay("oe-dropzones-container");
        // This container contains drop hint. The final rectangle showed to the user.
        this.dropzoneHintContainer = this.shared.makeLocalOverlay("oe-dropzone-hint-container");

        // Uncomment line for debugging tranparent zones
        // this.widgetHookContainer.classList.add("debug");
        // this.dropzonesContainer.classList.add("debug");

        this.scrollableElement = closestElement(this.editable.parentElement);
        while (
            this.scrollableElement &&
            getComputedStyle(this.scrollableElement).overflowY !== "auto"
        ) {
            this.scrollableElement = this.scrollableElement.parentElement;
        }
        this.scrollableElement = this.scrollableElement || this.editable;

        this.resetHooksNextMousemove = true;
        this.mutationObserver = new MutationObserver(() => {
            this.resetHooksNextMousemove = true;
            this.removeMoveWidget();
        });
        this.mutationObserver.observe(this.editable, {
            childList: true,
            subtree: true,
            characterData: true,
            characterDataOldValue: true,
        });
    }
    destroy() {
        super.destroy();
        this.intersectionObserver.disconnect();
        this.mutationObserver.disconnect();
        this.smoothScrollOnDrag && this.smoothScrollOnDrag.destroy();
    }
    intersectionObserverCallback(entries) {
        for (const entry of entries) {
            const element = entry.target;
            if (entry.isIntersecting) {
                this.visibleMovableElements.add(element);
                this.resetHooksNextMousemove = true;
            } else {
                this.visibleMovableElements.delete(element);
                const hookElement = this.elementHookMap.get(element);
                if (hookElement) {
                    // If hookElement is undefined, it means that this callback
                    // was called after a new element was inserted in the
                    // editable, but before the next updateHooks. The hook will
                    // be created when that happens.
                    hookElement.style.display = `none`;
                }
            }
        }
    }
    updateHooks() {
        const editableStyles = getComputedStyle(this.editable);
        this.editableRect = this.editable.getBoundingClientRect();
        const paddingLeft = parseInt(editableStyles.paddingLeft, 10) || 0;
        this.editableRect.x = this.editableRect.x + paddingLeft - (WIDGET_CONTAINER_WIDTH + 5);
        this.editableRect.width =
            this.editableRect.width - paddingLeft + (WIDGET_CONTAINER_WIDTH + 5);
        const containerRect = this.widgetHookContainer.getBoundingClientRect();
        const elements = this.getMovableElements();

        const elementsToGarbageCollect = new Set(this.elementHookMap.keys());
        for (const index in elements) {
            const element = elements[index];
            elementsToGarbageCollect.delete(element);
            let hookElement = this.elementHookMap.get(element);
            if (!hookElement) {
                hookElement = document.createElement("div");
                this.elementHookMap.set(element, hookElement);
                hookElement.classList.add("oe-dropzone-hook");
                hookElement.addEventListener("mouseenter", () => {
                    if (element !== this.currentMovableElement) {
                        this.setMovableElement(element);
                    }
                });
                this.widgetHookContainer.append(hookElement);
                hookElement.style.display = `none`;

                this.intersectionObserver.observe(element);
            }
            hookElement.style.zIndex = index;
        }
        // For all the elements that are not in the dom, remove their
        // corresponding hook.
        for (const element of elementsToGarbageCollect) {
            this.visibleMovableElements.delete(element);
            this.elementHookMap.get(element).remove();
            this.intersectionObserver.unobserve(element);
            this.elementHookMap.delete(element);
        }

        const visibleElements = [...this.visibleMovableElements];
        // Prevent layout thrashing by computing all the rects in advance.
        const elementRects = visibleElements.map((element) => element.getBoundingClientRect());
        for (const index in visibleElements) {
            const element = visibleElements[index];
            const elementRect = elementRects[index];
            const hookElement = this.elementHookMap.get(element);

            const style = getComputedStyle(element);
            const marginTop = parseInt(style.marginTop, 10) || 0;
            const marginBottom = parseInt(style.marginBottom, 10) || 0;
            let hookBox;
            if (element.tagName === "HR") {
                hookBox = new DOMRect(
                    elementRect.x - containerRect.left - WIDGET_CONTAINER_WIDTH,
                    elementRect.y - containerRect.top - marginTop,
                    elementRect.width + WIDGET_CONTAINER_WIDTH,
                    elementRect.height + marginTop + marginBottom
                );
            } else {
                hookBox = new DOMRect(
                    elementRect.x - containerRect.left - WIDGET_CONTAINER_WIDTH,
                    elementRect.y - containerRect.top - marginTop,
                    WIDGET_CONTAINER_WIDTH,
                    elementRect.height + marginTop + marginBottom
                );
            }

            hookElement.style.left = `${hookBox.x}px`;
            hookElement.style.top = `${hookBox.y}px`;
            hookElement.style.width = `${hookBox.width}px`;
            hookElement.style.height = `${hookBox.height}px`;
            hookElement.style.display = `block`;
        }
    }
    _updateAnchorWidgets(newAnchorWidget) {
        let movableElement =
            newAnchorWidget &&
            closestElement(newAnchorWidget, (node) => {
                return isNodeMovable(node) && node.matches(ALLOWED_ELEMENTS);
            });
        // Retrive the first list container from the ancestors.
        const listContainer =
            movableElement &&
            ancestors(movableElement, this.editable)
                .reverse()
                .find((n) => ["UL", "OL"].includes(n.tagName));
        movableElement = listContainer || movableElement;
        if (movableElement && movableElement !== this.currentMovableElement) {
            this.setMovableElement(movableElement);
        }
    }
    getMovableElements() {
        const elems = [];
        for (const el of this.editable.querySelectorAll(ALLOWED_ELEMENTS)) {
            if (isNodeMovable(el)) {
                elems.push(el);
            }
        }
        return elems;
    }
    getDroppableElements(draggableNode) {
        return this.getMovableElements().filter(
            (node) => !closestElement(node.parentElement, (n) => n === draggableNode)
        );
    }
    setMovableElement(movableElement) {
        this.removeMoveWidget();
        this.currentMovableElement = movableElement;
        this.getResource("setMovableElement").forEach((cb) => cb(movableElement));

        const containerRect = this.widgetContainer.getBoundingClientRect();
        const anchorBlockRect = this.currentMovableElement.getBoundingClientRect();
        const closestList = closestElement(this.currentMovableElement, "ul, ol"); // Prevent overlap bullets.
        const anchorX = closestList ? closestList.getBoundingClientRect().x : anchorBlockRect.x;
        let anchorY = anchorBlockRect.y;
        if (this.currentMovableElement.tagName.match(/H[1-6]/)) {
            anchorY += (anchorBlockRect.height - WIDGET_MOVE_SIZE) / 2;
        }

        this.moveWidget = this.document.createElement("div");
        this.moveWidget.className = "oe-sidewidget-move fa fa-sort";
        this.widgetContainer.append(this.moveWidget);

        let moveWidgetOffsetTop = 0;
        if (movableElement.tagName === "HR") {
            const style = getComputedStyle(movableElement);
            moveWidgetOffsetTop = parseInt(style.marginTop, 10) || 0;
        }

        this.moveWidget.style.width = `${WIDGET_MOVE_SIZE}px`;
        this.moveWidget.style.height = `${WIDGET_MOVE_SIZE}px`;
        this.moveWidget.style.top = `${anchorY - containerRect.y - moveWidgetOffsetTop}px`;
        this.moveWidget.style.left = `${anchorX - containerRect.x - WIDGET_CONTAINER_WIDTH}px`;

        if (this.scrollableElement) {
            this.smoothScrollOnDrag && this.smoothScrollOnDrag.destroy();
            // TODO: This should be made more generic, one hook for the entire
            // editable with each element handled.
            this.smoothScrollOnDrag = useNativeDraggable(simpleDraggableHook, {
                ref: { el: this.widgetContainer },
                elements: ".oe-sidewidget-move",
                onDragStart: () => this.startDropzones(movableElement, containerRect),
                onDragEnd: () => this._stopDropzones(movableElement),
                helper: () => {
                    const container = document.createElement("div");
                    container.append(movableElement.cloneNode(true));
                    const style = getComputedStyle(movableElement);
                    container.style.height = style.height;
                    container.style.width = style.width;
                    container.style.paddingLeft = "25px";
                    container.style.opacity = "0.4";
                    this.dragHelperContainer.append(container);
                    return container;
                },
            });
        }
    }
    removeMoveWidget() {
        this.getResource("unsetMovableElement").forEach((cb) => cb());
        this.moveWidget?.remove();
        this.moveWidget = undefined;
        this.currentMovableElement = undefined;
    }
    startDropzones(movableElement, containerRect, directions = ["north", "south"]) {
        this.removeMoveWidget();
        const elements = this.getDroppableElements(movableElement);

        this.dropzonesContainer.replaceChildren();
        this.editable.classList.add("oe-editor-dragging");

        for (const element of elements) {
            const originalRect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            const marginTop = parseInt(style.marginTop, 10);
            const marginBottom = parseInt(style.marginBottom, 10);
            const marginLeft = parseInt(style.marginLeft, 10);
            const marginRight = parseInt(style.marginRight, 10);

            const dropzoneRect = new DOMRect(
                originalRect.left - marginLeft - WIDGET_CONTAINER_WIDTH,
                originalRect.top - marginTop,
                originalRect.width + marginLeft + marginRight + WIDGET_CONTAINER_WIDTH,
                originalRect.height + marginTop + marginBottom
            );
            const dropzoneHintRect = new DOMRect(
                originalRect.left - marginLeft,
                originalRect.top - marginTop,
                originalRect.width + marginLeft + marginRight,
                originalRect.height + marginTop + marginBottom
            );

            const dropzoneBox = document.createElement("div");
            dropzoneBox.className = `oe-dropzone-box`;
            dropzoneBox.style.top = `${dropzoneRect.top - containerRect.top}px`;
            dropzoneBox.style.left = `${dropzoneRect.left - containerRect.left}px`;
            dropzoneBox.style.width = `${dropzoneRect.width}px`;
            dropzoneBox.style.height = `${dropzoneRect.height}px`;

            const dropzoneHintBox = document.createElement("div");
            dropzoneHintBox.className = `oe-dropzone-box`;
            dropzoneHintBox.style.top = `${dropzoneHintRect.top - containerRect.top}px`;
            dropzoneHintBox.style.left = `${dropzoneHintRect.left - containerRect.left}px`;
            dropzoneHintBox.style.width = `${dropzoneHintRect.width}px`;
            dropzoneHintBox.style.height = `${dropzoneHintRect.height}px`;

            const sideElements = {};
            for (const direction of directions) {
                const sideElement = document.createElement("div");
                sideElement.className = `oe-dropzone-box-side oe-dropzone-box-side-${direction}`;
                sideElements[direction] = sideElement;
                dropzoneBox.append(sideElement);
                const onEnter = () => {
                    this._currentZone = [direction];

                    removeDropHint();
                    this._currentDropHint = document.createElement("div");
                    this._currentDropHint.className = `oe-current-drop-hint`;
                    const currentDropHintSize = 4;
                    const currentDropHintSizeHalf = currentDropHintSize / 2;

                    if (direction === "north") {
                        this._currentDropHint.style["top"] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style["width"] = `100%`;
                        this._currentDropHint.style["height"] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ["top", element];
                    } else if (direction === "south") {
                        this._currentDropHint.style["bottom"] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style["width"] = `100%`;
                        this._currentDropHint.style["height"] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ["bottom", element];
                    } else if (direction === "west") {
                        this._currentDropHint.style["left"] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style["height"] = `100%`;
                        this._currentDropHint.style["width"] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ["left", element];
                    } else if (direction === "east") {
                        this._currentDropHint.style["right"] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style["height"] = `100%`;
                        this._currentDropHint.style["width"] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ["right", element];
                    }
                };
                sideElement.addEventListener("mouseenter", onEnter);
                sideElement.addEventListener("pointerenter", onEnter);
                const removeDropHint = () => {
                    if (this._currentDropHint) {
                        this._currentDropHint.remove();
                        this._currentDropHint = null;
                    }
                    this._currentDropHintElementPosition = null;
                };
                dropzoneBox.addEventListener("mouseleave", removeDropHint);
                dropzoneBox.addEventListener("pointerleave", removeDropHint);
            }

            this.dropzonesContainer.append(dropzoneBox);
            this.dropzoneHintContainer.append(dropzoneHintBox);
        }
    }
    _stopDropzones(movableElement) {
        this.editable.classList.remove("oe-editor-dragging");
        this.dropzonesContainer.replaceChildren();
        this.dropzoneHintContainer.replaceChildren();

        if (this._currentDropHintElementPosition) {
            const [position, focusElelement] = this._currentDropHintElementPosition;
            this._currentDropHintElementPosition = undefined;
            const previousParent = movableElement.parentElement;
            if (position === "top") {
                focusElelement.before(movableElement);
            } else if (position === "bottom") {
                focusElelement.after(movableElement);
            }
            if (previousParent.innerHTML.trim() === "") {
                const p = document.createElement("p");
                const br = document.createElement("br");
                p.append(br);
                previousParent.append(p);
            }
            const selectionPosition = endPos(movableElement);
            this.shared.setSelection({
                anchorNode: selectionPosition[0],
                anchorOffset: selectionPosition[1],
            });
            this.dispatch("ADD_STEP");
        }
    }
    onMousemove(e) {
        this._updateAnchorWidgets(e.target);
    }
    onDocumentKeydown() {
        // Hide the move widget upon keystroke for visual clarity and provide
        // visibility to a collaborative avatar.
        this.removeMoveWidget();
    }
    onDocumentMousemove(e) {
        if (this.resetHooksNextMousemove) {
            this.resetHooksNextMousemove = false;
            this.removeMoveWidget();
            this.updateHooks();
        }
        const clientX = e.clientX ?? e.touches?.[0]?.clientX;
        const clientY = e.clientY ?? e.touches?.[0]?.clientY;
        if (this.editableRect && !isPointInside(this.editableRect, clientX, clientY)) {
            this.removeMoveWidget();
        }
    }
}

function isNodeMovable(node) {
    return (
        node.parentElement?.getAttribute("contentEditable") === "true" &&
        !node.parentElement.closest(".o_editor_banner")
    );
}

function isPointInside(rect, x, y) {
    return rect.left <= x && rect.right >= x && rect.top <= y && rect.bottom >= y;
}

const simpleDraggableHook = {
    acceptedParams: {
        helper: [Function],
    },
    edgeScrolling: { enable: true },
    onComputeParams({ ctx, params }) {
        ctx.helper = params.helper;
        ctx.followCursor = false;
        ctx.tolerance = 0;
    },
    onDragStart({ ctx }) {
        ctx.current.element = ctx.helper();
        ctx.current.element.style.left = `${ctx.pointer.x + 10}px`;
        ctx.current.element.style.top = `${ctx.pointer.y + 10}px`;
        ctx.current.element.style.position = "fixed";
        // makeDraggableHook disables pointer events, we want them in this case
        document.body.classList.remove("pe-none");
        return ctx.current;
    },
    onDrag({ ctx }) {
        ctx.current.element.style.left = `${ctx.pointer.x}px`;
        ctx.current.element.style.top = `${ctx.pointer.y}px`;
    },
    onDragEnd({ ctx }) {
        ctx.current.element.remove();
        return ctx.current;
    },
};
