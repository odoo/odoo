/** @odoo-module */
import {
    ancestors,
    closestElement,
    resetOuids,
    setSelection,
} from '@web_editor/js/editor/odoo-editor/src/OdooEditor';
import { useNativeDraggable } from "@web_editor/js/editor/drag_and_drop";

const simpleDraggableHook = {
    acceptedParams: {
        helper: [Function],
    },
    edgeScrolling: { enable: true },
    onComputeParams({ ctx, params }) {
        ctx.helper = params.helper;
        ctx.followCursor = false;
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

const WIDGET_CONTAINER_WIDTH = 25;
const WIDGET_MOVE_SIZE = 20;

const ALLOWED_ELEMENTS = 'h1, h2, h3, p, hr, pre, blockquote, ul, ol, table, .o_knowledge_behavior_anchor, .o_text_columns, .o_editor_banner, .oe_movable';

export class MoveNodePlugin {
    constructor(options = {}) {
        this._options = options;

        this._intersectionObserver = new IntersectionObserver(
            this._intersectionObserverCallback.bind(this),
            {
                root: document,
            }
        );
        this._visibleMovableElements = new Set();
    }

    start() {
        this._editor = this._options.editor;
        this._editable = this._options.editor.editable;
        this._document = this._options.editor.document;
        this._elementHookMap = new Map();

        this._editor.addDomListener(this._editable, 'mousemove', this._onMousemove.bind(this), true);
        this._editor.addDomListener(this._editor.document, 'keydown', this._onDocumentKeydown.bind(this), true);
        this._editor.addDomListener(this._editor.document, 'mousemove', this._onDocumentMousemove.bind(this), true);

        const avatarContainer = this._editor.mainAbsoluteContainer.querySelector('[data-oe-absolute-container-id="oe-avatars-counters-container"]');

        // This container help to add zone into which the mouse can activate the move widget.
        this._widgetHookContainer = this._editor.makeAbsoluteContainer('oe-widget-hooks-container');
        avatarContainer.before(this._widgetHookContainer);
        // This container contains the differents widgets.
        this._widgetContainer = this._editor.makeAbsoluteContainer('oe-widgets-container');
        avatarContainer.before(this._widgetContainer);
        // This container contains the jquery helper element.
        this._dragHelperContainer = this._editor.makeAbsoluteContainer('oe-movenode-helper-container');
        avatarContainer.before(this._dragHelperContainer);
        // This container contains drop zones. They are the zones that handle where the drop should happen.
        this._dropzonesContainer = this._editor.makeAbsoluteContainer('oe-dropzones-container');
        avatarContainer.before(this._dropzonesContainer);
        // This container contains drop hint. The final rectangle showed to the user.
        this._dropzoneHintContainer = this._editor.makeAbsoluteContainer('oe-dropzone-hint-container');
        avatarContainer.before(this._dropzoneHintContainer);

        // Uncomment line for debugging tranparent zones
        // this._widgetHookContainer.classList.add('debug');
        // this._dropzonesContainer.classList.add('debug');

        this._scrollableElement = closestElement(this._editable.parentElement);
        while (this._scrollableElement && getComputedStyle(this._scrollableElement).overflowY !== 'auto') {
            this._scrollableElement = this._scrollableElement.parentElement;
        }
        this._scrollableElement = this._scrollableElement || this._editable;

        this._resetHooksNextMousemove = true;
        this.mutationObserver = new MutationObserver(() => {
            this._resetHooksNextMousemove = true;
            this._removeMoveWidget();
        });
        this.mutationObserver.observe(this._editable, {
            childList: true,
            subtree: true,
            characterData: true,
            characterDataOldValue: true,
        });
        this._editor.addDomListener(window, 'resize', this._updateHooks.bind(this));
        if (this._editor.document.defaultView !== window) {
            this._editor.addDomListener(this._editor.document.defaultView, 'resize', this._updateHooks.bind(this));
        }
    }
    destroy() {
        this._intersectionObserver.disconnect();
        this.mutationObserver.disconnect();
        this.smoothScrollOnDrag && this.smoothScrollOnDrag.destroy();
    }
    _intersectionObserverCallback(entries) {
        for (const entry of entries) {
            const element = entry.target;
            if (entry.isIntersecting) {
                this._visibleMovableElements.add(element);
                this._resetHooksNextMousemove = true;
            } else {
                this._visibleMovableElements.delete(element);
                const hookElement = this._elementHookMap.get(element);
                if (hookElement) {
                    // If hookElement is undefined, it means that this callback
                    // was called after a new element was inserted in the
                    // editable, but before the next _updateHooks. The hook will
                    // be created when that happens.
                    hookElement.style.display = `none`;
                }
            }
        }
    }
    _updateHooks() {
        const editableStyles = getComputedStyle(this._editable);
        this._editableRect = this._editable.getBoundingClientRect();
        const paddingLeft = parseInt(editableStyles.paddingLeft, 10) || 0;
        this._editableRect.x = this._editableRect.x + paddingLeft - (WIDGET_CONTAINER_WIDTH + 5);
        this._editableRect.width = this._editableRect.width - paddingLeft + (WIDGET_CONTAINER_WIDTH + 5);
        const containerRect = this._widgetHookContainer.getBoundingClientRect();
        const elements = this._getMovableElements();

        const elementsToGarbageCollect = new Set(this._elementHookMap.keys());
        for (const index in elements) {
            const element = elements[index];
            elementsToGarbageCollect.delete(element);
            let hookElement = this._elementHookMap.get(element);
            if (!hookElement) {
                hookElement = document.createElement('div');
                this._elementHookMap.set(element, hookElement);
                hookElement.classList.add('oe-dropzone-hook');
                hookElement.addEventListener('mouseenter', () => {
                    if (element !== this._currentMovableElement) {
                        this._setMovableElement(element);
                    }
                });
                this._widgetHookContainer.append(hookElement);
                hookElement.style.display = `none`;

                this._intersectionObserver.observe(element);
            }
            hookElement.style.zIndex = index;
        }
        // For all the elements that are not in the dom, remove their
        // corresponding hook.
        for (const element of elementsToGarbageCollect) {
            this._visibleMovableElements.delete(element);
            this._elementHookMap.get(element).remove();
            this._intersectionObserver.unobserve(element);
            this._elementHookMap.delete(element);
        }

        const visibleElements = [...this._visibleMovableElements];
        // Prevent layout thrashing by computing all the rects in advance.
        const elementRects = visibleElements.map((element) => element.getBoundingClientRect());
        for (const index in visibleElements) {
            const element = visibleElements[index];
            const elementRect = elementRects[index];
            const hookElement = this._elementHookMap.get(element);

            const style = getComputedStyle(element);
            const marginTop = parseInt(style.marginTop, 10) || 0;
            const marginBottom = parseInt(style.marginBottom, 10) || 0;
            let hookBox;
            if (element.tagName === 'HR') {
                hookBox = new DOMRect(
                    elementRect.x - containerRect.left - WIDGET_CONTAINER_WIDTH,
                    elementRect.y - containerRect.top - marginTop,
                    elementRect.width + WIDGET_CONTAINER_WIDTH,
                    elementRect.height + marginTop + marginBottom,
                );
            } else {
                hookBox = new DOMRect(
                    elementRect.x - containerRect.left - WIDGET_CONTAINER_WIDTH,
                    elementRect.y - containerRect.top - marginTop,
                    WIDGET_CONTAINER_WIDTH,
                    elementRect.height + marginTop + marginBottom,
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
        let movableElement = newAnchorWidget && closestElement(newAnchorWidget, (node) => {
            return isNodeMovable(node) && node.matches(ALLOWED_ELEMENTS);
        });
        // Retrive the first list container from the ancestors.
        const listContainer = movableElement && ancestors(movableElement, this._editable)
            .reverse()
            .find(n => ['UL', 'OL'].includes(n.tagName));
        movableElement = listContainer || movableElement;
        if (movableElement && (movableElement !== this._currentMovableElement)) {
            this._setMovableElement(movableElement);
        }
    }
    _getMovableElements() {
        return [...new Set([...this._editable.querySelectorAll(ALLOWED_ELEMENTS)])]
            .filter((node) => isNodeMovable(node));
    }
    _getDroppableElements(draggableNode) {
        return this._getMovableElements().filter((node) =>
            !closestElement(node.parentElement, (n) => n === draggableNode)
        );
    }
    _setMovableElement(movableElement) {
        this._removeMoveWidget();
        this._currentMovableElement = movableElement;
        this._editor.disableAvatarForElement(movableElement);

        const containerRect = this._widgetContainer.getBoundingClientRect();
        const anchorBlockRect = this._currentMovableElement.getBoundingClientRect();
        const closestList = closestElement(this._currentMovableElement, 'ul, ol'); // Prevent overlap bullets.
        const anchorX = closestList ? closestList.getBoundingClientRect().x : anchorBlockRect.x;
        let anchorY = anchorBlockRect.y;
        if (this._currentMovableElement.tagName.match(/H[1-6]/)) {
            anchorY += (anchorBlockRect.height - WIDGET_MOVE_SIZE) / 2;
        }

        this._moveWidget = this._document.createElement('div');
        this._moveWidget.className = 'oe-sidewidget-move fa fa-sort';
        this._widgetContainer.append(this._moveWidget);

        let moveWidgetOffsetTop = 0;
        if (movableElement.tagName === 'HR') {
            const style = getComputedStyle(movableElement);
            moveWidgetOffsetTop = parseInt(style.marginTop, 10) || 0;
        }

        this._moveWidget.style.width = `${WIDGET_MOVE_SIZE}px`;
        this._moveWidget.style.height = `${WIDGET_MOVE_SIZE}px`;
        this._moveWidget.style.top = `${anchorY - containerRect.y - moveWidgetOffsetTop}px`;
        this._moveWidget.style.left = `${anchorX - containerRect.x - WIDGET_CONTAINER_WIDTH}px`;

        if (this._scrollableElement) {
            this.smoothScrollOnDrag && this.smoothScrollOnDrag.destroy();
            // TODO: This should be made more generic, one hook for the entire
            // editable with each element handled.
            this.smoothScrollOnDrag = useNativeDraggable(simpleDraggableHook, {
                ref: { el: this._widgetContainer },
                elements: ".oe-sidewidget-move",
                onDragStart: () => this._startDropzones(movableElement, containerRect),
                onDragEnd: () => this._stopDropzones(movableElement),
                helper: () => {
                    const container = document.createElement('div');
                    container.append(movableElement.cloneNode(true));
                    const style = getComputedStyle(movableElement);
                    container.style.height = style.height;
                    container.style.width = style.width;
                    container.style.paddingLeft = '25px';
                    container.style.opacity = '0.4';
                    this._dragHelperContainer.append(container);
                    return container;
                }
            });
        }
    }
    _removeMoveWidget() {
        this._editor.enableAvatars();
        this._moveWidget?.remove();
        this._moveWidget = undefined;
        this._currentMovableElement = undefined;
    }
    _startDropzones(movableElement, containerRect, directions = ['north', 'south']) {
        this._removeMoveWidget();
        const elements = this._getDroppableElements(movableElement);

        this._dropzonesContainer.replaceChildren();
        this._editable.classList.add('oe-editor-dragging');

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
                originalRect.height + marginTop + marginBottom,
            );
            const dropzoneHintRect = new DOMRect(
                originalRect.left - marginLeft,
                originalRect.top - marginTop,
                originalRect.width + marginLeft + marginRight,
                originalRect.height + marginTop + marginBottom,
            );

            const dropzoneBox = document.createElement('div');
            dropzoneBox.className = `oe-dropzone-box`;
            dropzoneBox.style.top = `${dropzoneRect.top - containerRect.top}px`;
            dropzoneBox.style.left = `${dropzoneRect.left - containerRect.left}px`;
            dropzoneBox.style.width = `${dropzoneRect.width}px`;
            dropzoneBox.style.height = `${dropzoneRect.height}px`;

            const dropzoneHintBox = document.createElement('div');
            dropzoneHintBox.className = `oe-dropzone-box`;
            dropzoneHintBox.style.top = `${dropzoneHintRect.top - containerRect.top}px`;
            dropzoneHintBox.style.left = `${dropzoneHintRect.left - containerRect.left}px`;
            dropzoneHintBox.style.width = `${dropzoneHintRect.width}px`;
            dropzoneHintBox.style.height = `${dropzoneHintRect.height}px`;

            const sideElements = {};
            for (const direction of directions) {
                const sideElement = document.createElement('div');
                sideElement.className = `oe-dropzone-box-side oe-dropzone-box-side-${direction}`;
                sideElements[direction] = sideElement;
                dropzoneBox.append(sideElement);
                sideElement.addEventListener('mouseenter', () => {
                    this._currentZone = [direction];

                    removeDropHint();
                    this._currentDropHint = document.createElement('div');
                    this._currentDropHint.className = `oe-current-drop-hint`;
                    const currentDropHintSize = 4;
                    const currentDropHintSizeHalf = currentDropHintSize / 2;

                    if (direction === 'north') {
                        this._currentDropHint.style['top'] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style['width'] = `100%`;
                        this._currentDropHint.style['height'] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ['top', element];
                    } else if (direction === 'south') {
                        this._currentDropHint.style['bottom'] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style['width'] = `100%`;
                        this._currentDropHint.style['height'] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ['bottom', element];
                    } else if (direction === 'west') {
                        this._currentDropHint.style['left'] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style['height'] = `100%`;
                        this._currentDropHint.style['width'] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ['left', element];
                    } else if (direction === 'east') {
                        this._currentDropHint.style['right'] = `-${currentDropHintSizeHalf}px`;
                        this._currentDropHint.style['height'] = `100%`;
                        this._currentDropHint.style['width'] = `${currentDropHintSize}px`;
                        dropzoneHintBox.append(this._currentDropHint);
                        this._currentDropHintElementPosition = ['right', element];
                    }
                });
                const removeDropHint = () => {
                    if (this._currentDropHint) {
                        this._currentDropHint.remove();
                        this._currentDropHint = null;
                    }
                    this._currentDropHintCommand = null;
                }
                dropzoneBox.addEventListener('mouseleave', removeDropHint);
            }

            this._dropzonesContainer.append(dropzoneBox);
            this._dropzoneHintContainer.append(dropzoneHintBox);
        }
    }
    _stopDropzones(movableElement) {
        this._editable.classList.remove('oe-editor-dragging');
        this._dropzonesContainer.replaceChildren();
        this._dropzoneHintContainer.replaceChildren();

        if (this._currentDropHintElementPosition) {
            const [position, focusElelement] = this._currentDropHintElementPosition;
            this._currentDropHintElementPosition = undefined;
            const previousParent = movableElement.parentElement;
            if (position === 'top') {
                focusElelement.before(movableElement);
            } else if (position === 'bottom') {
                focusElelement.after(movableElement);
            }
            if (previousParent.innerHTML.trim() === '') {
                const p = document.createElement('p');
                const br = document.createElement('br');
                p.append(br);
                previousParent.append(p);
            }
            setSelection(
                movableElement,
                movableElement.childNodes.length
            );
            resetOuids(movableElement);
            this._editor.historyStep();
        }
    }
    _onMousemove(e) {
        this._updateAnchorWidgets(e.target);
    }
    _onDocumentKeydown() {
        // Hide the move widget upon keystroke for visual clarity and provide
        // visibility to a collaborative avatar.
        this._removeMoveWidget();
    }
    _onDocumentMousemove(e) {
        if(this._resetHooksNextMousemove) {
            this._resetHooksNextMousemove = false;
            this._removeMoveWidget();
            this._updateHooks();
        }
        if (this._editableRect && !isPointInside(this._editableRect, e.clientX, e.clientY)) {
            this._removeMoveWidget();
        }
    }
}

function isNodeMovable(node) {
    return node.parentElement?.getAttribute('contentEditable') === 'true' && !node.parentElement.closest('.o_editor_banner');
}

function isPointInside(rect, x, y) {
    return rect.left <= x &&
        rect.right >= x &&
        rect.top <= y &&
        rect.bottom >= y;
};
