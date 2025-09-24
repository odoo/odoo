import { useRef, useState } from "@web/owl2/utils";
import { Component, onMounted, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { closestScrollableY, getScrollingElement, isScrollableY } from "@web/core/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { closest } from "@web/core/utils/ui";
import { useDragAndDrop } from "@html_editor/utils/drag_and_drop";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { useSnippets } from "@html_builder/snippets/snippet_service";
import { useMatrixKeyNavigation } from "@html_builder/utils/keyboard_navigation";
import { Snippet } from "./snippet";
import { CustomInnerSnippet } from "./custom_inner_snippet";

/**
 * @typedef {import("@html_builder/core/drag_and_drop_plugin").DragState} DragState
 * @typedef {((arg: { snippetEl: HTMLElement }) => void)[]} on_snippet_dropped_handlers
 * @typedef {((arg: { snippetEl: HTMLElement, dragState: DragState }) => void)[]} on_snippet_dragged_handlers
 * @typedef {((arg: { droppedEl: HTMLElement, dropzoneEl: HTMLElement, dragState: DragState }) => void)[]} on_snippet_dropped_near_handlers
 * @typedef {((arg: { droppedEl: HTMLElement, dragState: DragState }) => void)[]} on_snippet_dropped_over_handlers
 * @typedef {((arg: { droppedEl: HTMLElement, dragState: DragState, x, y }) => void)[]} on_snippet_move_handlers
 * @typedef {((arg: { droppedEl: HTMLElement, dragState: DragState }) => void)[]} on_snippet_out_dropzone_handlers
 * @typedef {((arg: { droppedEl: HTMLElement, dragState: DragState }) => void)[]} on_snippet_over_dropzone_handlers
 */

export class BlockTab extends Component {
    static template = "html_builder.BlockTab";
    static components = { Snippet, CustomInnerSnippet };
    static props = {
        snippetsName: String,
        newInstalledModule: { type: String, optional: true }
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.popover = useService("popover");
        this.snippetModel = useSnippets(this.props.snippetsName);
        this.blockTabRef = useRef("block-tab");
        this.groupSnippetsContainer = useRef("group-snippets-container");
        this.innerSnippetsContainer = useRef("inner-snippets-container");
        // Needed to avoid race condition in tours.
        this.state = useState({ ongoingInsertion: false });

        this.onSnippetKeydown = useMatrixKeyNavigation(
            () => [this.groupSnippetsContainer.el, this.innerSnippetsContainer.el],
            ".o_snippet",
            ".o_snippet_thumbnail_area, .o_install_btn"
        );

        onMounted(() => {
            this.makeSnippetDraggable();
            if (this.props.newInstalledModule) {
                this.handlePostModuleInstall(this.props.newInstalledModule)
            }
        });

        onWillDestroy(() => {
            this.draggableComponent?.destroy();
        });
    }

    get document() {
        return this.env.editor.document;
    }

    get editable() {
        return this.env.editor.editable;
    }

    get shared() {
        return this.env.editor.shared;
    }

    /**
     * Opens and manages the snippet dialog after clicking on a snippet group,
     * and inserts the selected snippet in the page.
     *
     * @param {Object} snippet the clicked snippet group
     */
    async onSnippetGroupClick(snippet) {
        this.state.ongoingInsertion = true;
        await this.shared.blockTab.insertSnippetGroup(snippet);
        this.state.ongoingInsertion = false;
    }

    /**
     * Opens and manages the snippet dialog after dropping a snippet group.
     * If a snippet is selected in the dialog, it will replace the given
     * placeholder snippet.
     *
     * @param {Object} snippet the dropped snippet group
     * @param {HTMLElement} hookEl the placeholder snippet
     */
    async onSnippetGroupDrop(snippet, cancelDragAndDrop, dragState) {
        const { snippetEl: hookEl } = dragState;
        this.state.ongoingInsertion = true;
        // Exclude the snippets that are not allowed to be dropped at the
        // current position.
        const hookParentEl = hookEl.parentElement;
        this.snippetModel.snippetStructures.forEach((snippet) => {
            const { selectorChildren } = this.shared.dropzone.getSelectors(snippet.content);
            snippet.isExcluded = ![...selectorChildren].some((el) => el === hookParentEl);
        });

        // Open the snippet dialog.
        let selectedSnippetEl;
        await new Promise((resolve) => {
            this.snippetModel.openSnippetDialog(
                snippet,
                {
                    onSelect: (snippet) => {
                        selectedSnippetEl = snippet.content.cloneNode(true);
                        hookEl.replaceWith(selectedSnippetEl);
                        return selectedSnippetEl;
                    },
                    onClose: () => {
                        if (!selectedSnippetEl) {
                            hookEl.remove();
                        }
                        this.snippetModel.snippetStructures.forEach(
                            (snippet) => delete snippet.isExcluded
                        );
                        resolve();
                    },
                },
                this.env.editor
            );
        });

        if (selectedSnippetEl) {
            await this.shared.blockTab.scrollToDroppedSnippet(selectedSnippetEl);
            await this.shared.blockTab.processDroppedSnippet(
                selectedSnippetEl,
                cancelDragAndDrop,
                dragState
            );
        } else {
            cancelDragAndDrop();
        }
        this.state.ongoingInsertion = false;
    }

    /**
     * Shows a tooltip telling to drag the snippet when clicking on it.
     *
     * @param {Event} ev
     */
    showSnippetTooltip(ev) {
        const snippetEl = ev.currentTarget.closest(".o_snippet.o_draggable");
        if (snippetEl) {
            this.hideSnippetToolTip?.();
            this.hideSnippetToolTip = this.popover.add(snippetEl, Tooltip, {
                tooltip: _t("Drag and drop the building block"),
            });
            setTimeout(this.hideSnippetToolTip, 1500);
        }
    }

    // TODO bounce animation on click if empty editable

    /**
     * Initializes the drag and drop for the snippets in the block tabs.
     */
    makeSnippetDraggable() {
        let dropzoneEls = [];
        let dragAndDropResolve;

        let snippet, snippetEl, isSnippetGroup, cancelDragAndDrop, dragState;

        const iframeWindow =
            this.document.defaultView !== window ? this.document.defaultView : false;

        const scrollingElement = () => {
            let scrollingElement =
                this.shared.dropzone.getDropRootElement() ||
                getScrollingElement(this.document) ||
                this.editable.querySelector(".o_savable");
            if (!isScrollableY(scrollingElement)) {
                scrollingElement =
                    closestScrollableY(this.document.defaultView.frameElement) ?? scrollingElement;
            }
            return scrollingElement;
        };

        const dragAndDropOptions = {
            ref: { el: this.blockTabRef.el },
            iframeWindow,
            cursor: "move",
            el: this.blockTabRef.el,
            elements: ".o_snippet.o_draggable",
            scrollingElement,
            handle: ".o_snippet_thumbnail:not(.o_we_ongoing_insertion .o_snippet_thumbnail)",
            dropzones: () => dropzoneEls,
            helper: ({ element, helperOffset }) => {
                snippet = element;
                const draggedEl = element.cloneNode(true);
                draggedEl
                    .querySelectorAll(
                        ".o_snippet_thumbnail_title, .o_snippet_thumbnail_area, .rename-delete-buttons"
                    )
                    .forEach((el) => el.remove());
                draggedEl.style.position = "fixed";
                document.body.append(draggedEl);
                // Center the helper on the thumbnail image.
                const thumbnailImgEl = element.querySelector(".o_snippet_thumbnail_img");
                helperOffset.x = thumbnailImgEl.offsetWidth / 2;
                helperOffset.y = thumbnailImgEl.offsetHeight / 2;
                return draggedEl;
            },
            onDragStart: ({ element }) => {
                const dragAndDropProm = new Promise(
                    (resolve) => (dragAndDropResolve = () => resolve())
                );
                this.shared.operation.next(async () => await dragAndDropProm, {
                    withLoadingEffect: false,
                    canTimeout: false,
                });
                const restoreDragSavePoint = this.shared.history.makeSavePoint();
                cancelDragAndDrop = () => {
                    this.shared.dropzone.removeDropzones();
                    // Undo the changes needed to ease the drag and drop.
                    dragState.restoreCallbacks?.forEach((restore) => restore());
                    restoreDragSavePoint();
                };
                this.hideSnippetToolTip?.();

                this.document.body.classList.add("oe_dropzone_active");
                this.state.ongoingInsertion = true;

                dragState = {};
                dropzoneEls = [];

                // Stop marking the elements with mutations as dirty and make
                // some changes on the page to ease the drag and drop.
                dragState.restoreCallbacks = this.env.editor
                    .trigger("on_prepare_drag_handlers")
                    .reverse();

                const category = element.closest(".o_snippets_container").id;
                const id = element.dataset.id;
                snippet = this.snippetModel.getSnippet(category, id);
                snippetEl = snippet.content.cloneNode(true);
                isSnippetGroup = category === "snippet_groups";

                // Check if the snippet is inline. Add it temporarily to the
                // page to compute its style and get its `display` property.
                this.document.body.appendChild(snippetEl);
                const snippetStyle = window.getComputedStyle(snippetEl);
                const isInlineSnippet = snippetStyle.display.includes("inline");
                snippetEl.remove();

                // Color-customize the snippet dynamic SVGs with the current
                // theme colors.
                const dynamicSvgEls = [
                    ...snippetEl.querySelectorAll(
                        'img[src^="/html_editor/shape/"], img[src^="/web_editor/shape/"]'
                    ),
                ];
                dynamicSvgEls.forEach((dynamicSvgEl) => {
                    const colorCustomizedURL = new URL(
                        dynamicSvgEl.getAttribute("src"),
                        window.location.origin
                    );
                    colorCustomizedURL.searchParams.forEach((value, key) => {
                        const match = key.match(/^c([1-5])$/);
                        if (match) {
                            colorCustomizedURL.searchParams.set(
                                key,
                                getCSSVariableValue(
                                    `o-color-${match[1]}`,
                                    this.document.defaultView.getComputedStyle(
                                        this.document.documentElement
                                    )
                                )
                            );
                        }
                    });
                    dynamicSvgEl.src = colorCustomizedURL.pathname + colorCustomizedURL.search;
                });

                const dragImagePreviewSrc = snippet.dragImagePreviewSrc;
                // Use an image as a placeholder for a snippet that takes too
                // long to load or doesn’t load when dragging over a dropzone.
                if (dragImagePreviewSrc) {
                    const dragPreviewEl = document.createElement("div");
                    dragPreviewEl.classList.add("o_snippet_drag_preview");
                    const imgPreviewEl = document.createElement("img");
                    imgPreviewEl.src = dragImagePreviewSrc;
                    imgPreviewEl.classList.add("img-fluid", "mx-auto");
                    dragPreviewEl.appendChild(imgPreviewEl);
                    snippetEl.appendChild(dragPreviewEl);
                    snippetEl.classList.add("o_snippet_previewing_on_drag");
                }
                // The dragged element may change while dragging.
                Object.assign(dragState, { draggedEl: snippetEl, snippetEl, snippet });

                // Add the dropzones.
                const withGrids =
                    !isSnippetGroup &&
                    (this.env.editor.config.isMobileView(this.editable) ? "filterOnly" : true);
                const selectors = this.shared.dropzone.getSelectors(snippetEl, false, withGrids);
                dropzoneEls = this.shared.dropzone.activateDropzones(selectors, {
                    toInsertInline: isInlineSnippet,
                });

                this.env.editor.trigger("on_snippet_dragged_handlers", {
                    snippetEl,
                    dragState,
                });
            },
            dropzoneOver: ({ dropzone }) => {
                const dropzoneEl = dropzone.el;
                if (isSnippetGroup) {
                    dropzoneEl.classList.add("o_dropzone_highlighted");
                    dragState.currentDropzoneEl = dropzoneEl;
                    return;
                }
                dropzoneEl.after(dragState.draggedEl);
                dropzoneEl.classList.add("invisible");
                dragState.currentDropzoneEl = dropzoneEl;

                this.env.editor.trigger("on_snippet_over_dropzone_handlers", {
                    snippetEl,
                    dragState,
                });
            },
            onDrag: ({ x, y }) => {
                if (!dragState.currentDropzoneEl) {
                    return;
                }

                this.env.editor.trigger("on_snippet_move_handlers", {
                    snippetEl,
                    dragState,
                    x,
                    y,
                });
            },
            dropzoneOut: ({ dropzone }) => {
                const dropzoneEl = dropzone.el;
                if (isSnippetGroup) {
                    dropzoneEl.classList.remove("o_dropzone_highlighted");
                    dragState.currentDropzoneEl = null;
                    return;
                }

                this.env.editor.trigger("on_snippet_out_dropzone_handlers", {
                    snippetEl,
                    dragState,
                });

                dragState.draggedEl.remove();
                dropzoneEl.classList.remove("invisible");
                dragState.currentDropzoneEl = null;
            },
            onDragEnd: async ({ x, y, helper }) => {
                this.document.body.classList.remove("oe_dropzone_active");
                let currentDropzoneEl = dragState.currentDropzoneEl;
                const isDroppedOver = !!currentDropzoneEl;

                // If the snippet was dropped outside of a dropzone, find the
                // dropzone that is the nearest to the dropping point.
                if (!currentDropzoneEl) {
                    const blockTabRect = this.blockTabRef.el.getBoundingClientRect();
                    const helperWidth = helper.getBoundingClientRect().width;
                    const isRTL = document.body.classList.contains("o_rtl");
                    const isOutOfBlockTab = isRTL
                        ? blockTabRect.left + blockTabRect.width < x - helperWidth / 2
                        : x + helperWidth / 2 < blockTabRect.left;
                    if (y > 3 && isOutOfBlockTab) {
                        const closestDropzoneEl = closest(dropzoneEls, { x, y });
                        if (closestDropzoneEl) {
                            currentDropzoneEl = closestDropzoneEl;
                        }
                    }
                }

                if (currentDropzoneEl) {
                    let draggedEl = dragState.draggedEl;

                    // If a preview image was displayed during the drag, we remove it.
                    draggedEl.querySelector(".o_snippet_drag_preview")?.remove();
                    dragState.snippetEl.classList.remove("o_snippet_previewing_on_drag");

                    if (isDroppedOver) {
                        this.env.editor.trigger("on_snippet_dropped_over_handlers", {
                            droppedEl: draggedEl,
                            dragState,
                        });
                    } else {
                        currentDropzoneEl.after(draggedEl);
                        this.env.editor.trigger("on_snippet_dropped_near_handlers", {
                            droppedEl: draggedEl,
                            dropzoneEl: currentDropzoneEl,
                            dragState,
                        });
                    }
                    // The dragged element may have changed, so get it again.
                    draggedEl = dragState.draggedEl;

                    // In order to mark only the concerned elements as dirty,
                    // remove the element, then replay the drop after
                    // re-allowing to mark dirty.
                    draggedEl.remove();

                    // Undo the changes needed to ease the drag and drop and
                    // re-allow to mark dirty.
                    dragState.restoreCallbacks.forEach((restore) => restore());
                    dragState.restoreCallbacks = null;

                    // Replay the drop.
                    currentDropzoneEl.after(draggedEl);
                    this.shared.dropzone.removeDropzones();

                    // Process the dropped element.
                    if (!isSnippetGroup) {
                        await this.shared.blockTab.processDroppedSnippet(
                            snippetEl,
                            cancelDragAndDrop,
                            dragState
                        );
                    } else {
                        this.shared.operation.next(
                            async () => {
                                await this.onSnippetGroupDrop(
                                    snippet,
                                    cancelDragAndDrop,
                                    dragState
                                );
                            },
                            {
                                withLoadingEffect: false,
                                shouldInterceptClick: true,
                                canTimeout: false,
                            }
                        );
                    }
                } else {
                    cancelDragAndDrop();
                }

                this.state.ongoingInsertion = false;
                dragAndDropResolve();
            },
        };

        this.draggableComponent = useDragAndDrop(dragAndDropOptions);
    }

    /**
     * Opens the corresponding snippet group dialog after the installation of a
     * newly installed snippet module.
     *
     * @param {string} newInstalledModule - The JSON object containing title of
     * the snippet group to open.
     */
    async handlePostModuleInstall(newInstalledModule) {
        const { snippetTitle } = JSON.parse(
            decodeURIComponent(newInstalledModule)
        );
        if (snippetTitle) {
            const snippet = this.snippetModel.snippetGroups.find(
                (snippetEl) => snippetEl.title === snippetTitle
            );
            if (snippet) {
                await this.onSnippetGroupClick(snippet);
            }
        }
    }
}
