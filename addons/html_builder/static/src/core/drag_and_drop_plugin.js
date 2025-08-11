import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { useDragAndDrop } from "@html_editor/utils/drag_and_drop";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { closest, touching } from "@web/core/utils/ui";
import { clamp } from "@web/core/utils/numbers";
import { rowSize } from "@html_builder/utils/grid_layout_utils";
import { isEditable, isVisible } from "@html_builder/utils/utils";
import { DragAndDropMoveHandle } from "./drag_and_drop_move_handle";

export class DragAndDropPlugin extends Plugin {
    static id = "dragAndDrop";
    static dependencies = ["dropzone", "history", "operation", "builderOptions"];
    resources = {
        has_overlay_options: { hasOption: (el) => this.isDraggable(el) },
        get_overlay_buttons: withSequence(1, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        system_classes: ["o_draggable"],
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.dropzoneSelectors = this.getResource("dropzone_selector");
        this.overlayTarget = null;
    }

    destroy() {
        this.draggableComponent?.destroy();
        this.draggableComponentImgs?.destroy();
    }

    cleanForSave({ root }) {
        [root, ...root.querySelectorAll(".o_draggable")].forEach((el) => {
            el.classList.remove("o_draggable");
        });
    }

    isDraggable(el) {
        const isDraggable =
            isEditable(el.parentNode) &&
            !el.matches(".oe_unmovable") &&
            !!this.dropzoneSelectors.find(
                ({ selector, exclude = false }) => el.matches(selector) && !el.matches(exclude)
            );
        if (!isDraggable) {
            return false;
        }

        for (const isDraggable of this.getResource("is_draggable_handlers")) {
            if (!isDraggable(el)) {
                return false;
            }
        }
        return true;
    }

    getActiveOverlayButtons(target) {
        if (!this.isDraggable(target)) {
            this.overlayTarget = null;
            this.draggableComponent?.destroy();
            this.draggableComponentImgs?.destroy();
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        buttons.push({
            Component: DragAndDropMoveHandle,
            props: {
                onRenderedCallback: () => {
                    this.draggableComponent?.destroy();
                    this.draggableComponentImgs?.destroy();

                    this.draggableComponent = this.initDragAndDrop(
                        ".o_move_handle",
                        ".o_overlay_options",
                        document.querySelector(".o_move_handle")
                    );
                    if (!this.overlayTarget.matches("section")) {
                        this.draggableComponentImgs = this.initDragAndDrop(
                            "img",
                            ".o_draggable",
                            this.overlayTarget
                        );
                    }
                },
            },
        });
        return buttons;
    }

    /**
     * Initializes the drag and drop handles.
     *
     * @param {String} handleSelector a selector targeting the handle to drag
     * @param {String} elementsSelector a selector targeting the element that
     *   will be dragged
     * @param {HTMLElement} element the element to listen for drag events
     * @returns {Object}
     */
    initDragAndDrop(handleSelector, elementsSelector, element) {
        let dropzoneEls = [];
        let dragAndDropResolve;

        const iframeWindow =
            this.document.defaultView !== window ? this.document.defaultView : false;

        const scrollingElement = () =>
            this.dependencies.dropzone.getDropRootElement() || getScrollingElement(this.document);

        const dragAndDropOptions = {
            ref: { el: element },
            iframeWindow,
            cursor: "move",
            elements: elementsSelector,
            scrollingElement,
            handle: handleSelector,
            enable: () => !!document.querySelector(".o_move_handle") || this.dragStarted, // Still needed ?
            dropzones: () => dropzoneEls,
            helper: ({ helperOffset }) => {
                const draggedEl = document.createElement("div");
                draggedEl.classList.add("o_drag_move_helper");
                Object.assign(draggedEl.style, {
                    width: "24px",
                    height: "24px",
                });
                document.body.append(draggedEl);
                helperOffset.x = 12;
                helperOffset.y = 12;
                return draggedEl;
            },
            onDragStart: ({ x, y }) => {
                const dragAndDropProm = new Promise(
                    (resolve) => (dragAndDropResolve = () => resolve())
                );
                this.dependencies.operation.next(async () => await dragAndDropProm, {
                    withLoadingEffect: false,
                });
                const restoreDragSavePoint = this.dependencies.history.makeSavePoint();
                this.cancelDragAndDrop = () => {
                    this.dependencies.dropzone.removeDropzones();
                    // Undo the changes needed to ease the drag and drop.
                    this.dragState.restoreCallbacks?.forEach((restore) => restore());
                    restoreDragSavePoint();
                    dragAndDropResolve();
                    this.dependencies["builderOptions"].updateContainers(this.overlayTarget);
                };

                this.dragStarted = true;
                this.dragState = {};
                dropzoneEls = [];

                // Bound the mouse for the case where we drag from an image.
                // Bound the Y mouse position to not escape the grid too easily.
                let targetRect = this.overlayTarget.getBoundingClientRect();
                const gridRowSize = rowSize;
                const boundedYMousePosition = clamp(
                    y,
                    targetRect.top + 12, // helper offset
                    targetRect.bottom - gridRowSize // height minus one grid row
                );
                this.dragState.mousePositionYOnElement = boundedYMousePosition - targetRect.y;
                this.dragState.mousePositionXOnElement = x - targetRect.x;

                // Stop marking the elements with mutations as dirty and make
                // some changes on the page to ease the drag and drop.
                const restoreCallbacks = [];
                for (const prepareDrag of this.getResource("on_prepare_drag_handlers")) {
                    const restore = prepareDrag();
                    restoreCallbacks.unshift(restore);
                }
                this.dragState.restoreCallbacks = restoreCallbacks;

                this.dispatchTo("on_element_dragged_handlers", {
                    draggedEl: this.overlayTarget,
                    dragState: this.dragState,
                });

                // Storing the element starting top and middle position.
                targetRect = this.overlayTarget.getBoundingClientRect();
                this.dragState.startTop = targetRect.top;
                this.dragState.startMiddle = targetRect.left + targetRect.width / 2;
                this.dragState.overFirstDropzone = true;

                // Check if the element is inline.
                const targetStyle = window.getComputedStyle(this.overlayTarget);
                const toInsertInline = targetStyle.display.includes("inline");

                // Store the parent and siblings.
                const parentEl = this.overlayTarget.parentElement;
                this.dragState.startParentEl = parentEl;
                this.dragState.startPreviousEl = this.overlayTarget.previousElementSibling;
                this.dragState.startNextEl = this.overlayTarget.nextElementSibling;

                // Add a clone, to allow to drop where it started.
                const visibleSiblingEl = [...parentEl.children].find(
                    (el) => el !== this.overlayTarget && isVisible(el)
                );
                if (parentEl.children.length === 1 || !visibleSiblingEl) {
                    const dropCloneEl = document.createElement("div");
                    dropCloneEl.classList.add("oe_drop_clone");
                    dropCloneEl.style.visibility = "hidden";
                    this.overlayTarget.after(dropCloneEl);
                    this.dragState.dropCloneEl = dropCloneEl;
                }

                // Get the dropzone selectors.
                const selectors = this.dependencies.dropzone.getSelectors(
                    this.overlayTarget,
                    true,
                    true
                );

                // Remove the dragged element and deactivate the options.
                this.overlayTarget.remove();
                this.dependencies["builderOptions"].deactivateContainers();

                // Add the dropzones.
                dropzoneEls = this.dependencies.dropzone.activateDropzones(selectors, {
                    toInsertInline,
                });
            },
            dropzoneOver: ({ dropzone }) => {
                const dropzoneEl = dropzone.el;

                // Prevent the element to be trapped in an upper dropzone at the
                // start of the drag.
                if (this.dragState.overFirstDropzone) {
                    this.dragState.overFirstDropzone = false;
                    const { startTop, startMiddle } = this.dragState;
                    // The element is considered as glued to the dropzone if the
                    // dropzone is above and if it is touching the initial
                    // helper position.
                    const helperRect = {
                        x: startMiddle - 12,
                        y: startTop - 24,
                        width: 24,
                        height: 24,
                    };
                    const dropzoneRect = dropzoneEl.getBoundingClientRect();
                    const dropzoneBottom = dropzoneRect.bottom;
                    const isGluedToDropzone =
                        startTop >= dropzoneBottom && !!touching([dropzoneEl], helperRect).length;
                    if (isGluedToDropzone) {
                        return;
                    }
                }

                dropzoneEl.classList.add("invisible");
                dropzoneEl.after(this.overlayTarget);
                this.dragState.currentDropzoneEl = dropzoneEl;

                this.dispatchTo("on_element_over_dropzone_handlers", {
                    draggedEl: this.overlayTarget,
                    dragState: this.dragState,
                });
            },
            onDrag: ({ x, y }) => {
                if (!this.dragState.currentDropzoneEl) {
                    return;
                }

                this.dispatchTo("on_element_move_handlers", {
                    draggedEl: this.overlayTarget,
                    dragState: this.dragState,
                    x,
                    y,
                });
            },
            dropzoneOut: () => {
                const dropzoneEl = this.dragState.currentDropzoneEl;
                if (!dropzoneEl) {
                    return;
                }

                this.dispatchTo("on_element_out_dropzone_handlers", {
                    draggedEl: this.overlayTarget,
                    dragState: this.dragState,
                });

                this.overlayTarget.remove();
                dropzoneEl.classList.remove("invisible");
                this.dragState.currentDropzoneEl = null;
            },
            onDragEnd: async ({ x, y }) => {
                this.dragStarted = false;
                let currentDropzoneEl = this.dragState.currentDropzoneEl;
                const isDroppedOver = !!currentDropzoneEl;

                // If the snippet was dropped outside of a dropzone, find the
                // dropzone that is the nearest to the dropping point.
                if (!currentDropzoneEl) {
                    const closestDropzoneEl = closest(dropzoneEls, { x, y });
                    if (!closestDropzoneEl) {
                        this.cancelDragAndDrop();
                        return;
                    }
                    currentDropzoneEl = closestDropzoneEl;
                }

                if (isDroppedOver) {
                    this.dispatchTo("on_element_dropped_over_handlers", {
                        droppedEl: this.overlayTarget,
                        dragState: this.dragState,
                    });
                } else {
                    currentDropzoneEl.after(this.overlayTarget);
                    this.dispatchTo("on_element_dropped_near_handlers", {
                        droppedEl: this.overlayTarget,
                        dropzoneEl: currentDropzoneEl,
                        dragState: this.dragState,
                    });
                }

                // In order to mark only the concerned elements as dirty, place
                // the element back where it started. The move will then be
                // replayed after re-allowing to mark dirty.
                const { startPreviousEl, startNextEl, startParentEl } = this.dragState;
                if (startPreviousEl) {
                    startPreviousEl.after(this.overlayTarget);
                } else if (startNextEl) {
                    startNextEl.before(this.overlayTarget);
                } else {
                    startParentEl.prepend(this.overlayTarget);
                }

                // Undo the changes needed to ease the drag and drop and
                // re-allow to mark dirty.
                this.dragState.restoreCallbacks.forEach((restore) => restore());
                this.dragState.restoreCallbacks = null;

                // Replay the move.
                currentDropzoneEl.after(this.overlayTarget);

                this.dependencies.dropzone.removeDropzones();
                this.dragState.dropCloneEl?.remove();

                // Process the dropped element.
                for (const onElementDropped of this.getResource("on_element_dropped_handlers")) {
                    const cancel = await onElementDropped({
                        droppedEl: this.overlayTarget,
                        dragState: this.dragState,
                    });
                    // Cancel everything if the resource asked to.
                    if (cancel) {
                        this.cancelDragAndDrop();
                        return;
                    }
                }

                // Add a history step only if the element was not dropped where
                // it was before, otherwise cancel everything.
                let hasSamePositionAsStart;
                if ("hasSamePositionAsStart" in this.dragState) {
                    hasSamePositionAsStart = this.dragState.hasSamePositionAsStart();
                } else {
                    const previousEl = this.overlayTarget.previousElementSibling;
                    const nextEl = this.overlayTarget.nextElementSibling;
                    const { startPreviousEl, startNextEl } = this.dragState;
                    hasSamePositionAsStart =
                        startPreviousEl === previousEl && startNextEl === nextEl;
                }
                if (!hasSamePositionAsStart) {
                    this.dependencies.history.addStep();
                } else {
                    this.cancelDragAndDrop();
                    return;
                }

                dragAndDropResolve();
                this.dependencies["builderOptions"].updateContainers(this.overlayTarget);
            },
        };

        return useDragAndDrop(dragAndDropOptions);
    }
}
