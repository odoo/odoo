import { Component, onMounted, onWillDestroy, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { closest } from "@web/core/utils/ui";
import { useDragAndDrop } from "@html_editor/utils/drag_and_drop";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";
import { scrollToWindow } from "@html_builder/utils/utils";
import { Snippet } from "./snippet";
import { CustomInnerSnippet } from "./custom_inner_snippet";

export class BlockTab extends Component {
    static template = "html_builder.BlockTab";
    static components = { Snippet, CustomInnerSnippet };
    static props = {};

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.popover = useService("popover");
        this.snippetModel = useState(useService("html_builder.snippets"));
        this.blockTabRef = useRef("block-tab");
        // Needed to avoid race condition in tours.
        this.state = useState({ ongoingInsertion: false });

        onMounted(() => {
            this.makeSnippetDraggable();
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

    get resources() {
        return this.env.editor.resources;
    }

    onSnippetGroupClick(snippet) {
        this.shared.operation.next(
            async () => {
                let snippetEl;
                this.state.ongoingInsertion = true;
                await new Promise((resolve) => {
                    this.snippetModel.openSnippetDialog(snippet, {
                        onSelect: (snippet) => {
                            snippetEl = snippet.content.cloneNode(true);
                            const selectors = this.shared.dropzone.getSelectors(snippetEl, snippet);
                            // Add the dropzones corresponding to the selected
                            // snippet and make them invisible.
                            const dropzoneEls = this.shared.dropzone.activateDropzones(selectors);
                            this.editable
                                .querySelectorAll(".oe_drop_zone")
                                .forEach((dropzoneEl) => dropzoneEl.classList.add("invisible"));

                            // Find the dropzone closest to the center of the
                            // viewport.
                            const iframeWindow = this.document.defaultView;
                            const viewPortCenterPoint = {
                                x: iframeWindow.innerWidth / 2,
                                y: iframeWindow.innerHeight / 2,
                            };
                            const closestDropzoneEl = closest(dropzoneEls, viewPortCenterPoint);
                            // Insert the selected snippet.
                            closestDropzoneEl.after(snippetEl);
                            this.shared.dropzone.removeDropzones();
                            return snippetEl;
                        },
                        onClose: () => {
                            resolve();
                        },
                    });
                });

                if (snippetEl) {
                    this.processDroppedSnippet(snippetEl);
                }
                this.state.ongoingInsertion = false;
            },
            { withLoadingEffect: false }
        );
    }

    /**
     * Opens and manages the snippet dialog after dropping a snippet group
     * If a snippet is selected in the dialog, it will replace the given
     * placeholder snippet.
     *
     * @param {Object} snippet the dropped snippet group
     * @param {HTMLElement} hookEl the placeholder snippet
     */
    async onSnippetGroupDrop(snippet, hookEl) {
        this.state.ongoingInsertion = true;
        // Exclude the snippets that are not allowed to be dropped at the
        // current position.
        const hookParentEl = hookEl.parentElement;
        this.snippetModel.snippetStructures.forEach((snippet) => {
            const { selectorChildren } = this.shared.dropzone.getSelectors(
                snippet.content,
                snippet
            );
            snippet.isExcluded = ![...selectorChildren].some((el) => el === hookParentEl);
        });

        // Open the snippet dialog.
        let selectedSnippetEl;
        await new Promise((resolve) => {
            this.snippetModel.openSnippetDialog(snippet, {
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
            });
        });

        if (selectedSnippetEl) {
            this.processDroppedSnippet(selectedSnippetEl);
        } else {
            this.cancelDragAndDrop();
        }
        this.state.ongoingInsertion = false;
        delete this.cancelDragAndDrop;
    }

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

    makeSnippetDraggable() {
        let dropzoneEls = [];
        let dragAndDropResolve;

        let snippet, snippetEl, isSnippetGroup;

        const iframeWindow =
            this.document.defaultView !== window ? this.document.defaultView : false;

        const scrollingElement = () =>
            this.shared.dropzone.getDropRootElement() ||
            this.editable.querySelector(".o_notebook") ||
            getScrollingElement(this.document) ||
            this.editable.querySelector(".o_editable");

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
                this.cancelDragAndDrop = this.shared.history.makeSavePoint();
                this.hideSnippetToolTip?.();

                this.shared.operation.next(
                    async () => {
                        await new Promise((resolve) => (dragAndDropResolve = () => resolve()));
                    },
                    { withLoadingEffect: false }
                );

                this.document.body.classList.add("oe_dropzone_active");
                this.state.ongoingInsertion = true;

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
                                getCSSVariableValue(`o-color-${match[1]}`)
                            );
                        }
                    });
                    dynamicSvgEl.src = colorCustomizedURL.pathname + colorCustomizedURL.search;
                });

                const selectors = this.shared.dropzone.getSelectors(snippetEl, snippet);
                dropzoneEls = this.shared.dropzone.activateDropzones(selectors, {
                    toInsertInline: isInlineSnippet,
                });
                this.onDropzoneStart();
            },
            dropzoneOver: ({ dropzone }) => {
                const dropzoneEl = dropzone.el;
                if (isSnippetGroup) {
                    dropzoneEl.classList.add("o_dropzone_highlighted");
                    return;
                }
                dropzoneEl.after(snippetEl);
                dropzoneEl.classList.add("invisible");
                this.onDropZoneOver();

                // Preview the snippet correctly.
                // Note: no async previews, in order to not slow down the drag.
                this.cancelSnippetPreview = this.shared.history.makeSavePoint();
                this.resources["on_snippet_preview_handlers"]?.forEach((onSnippetPreview) =>
                    onSnippetPreview({ snippetEl })
                );
            },
            dropzoneOut: ({ dropzone }) => {
                const dropzoneEl = dropzone.el;
                if (isSnippetGroup) {
                    dropzoneEl.classList.remove("o_dropzone_highlighted");
                    return;
                }
                // Undo the preview
                this.cancelSnippetPreview();
                delete this.cancelSnippetPreview;

                snippetEl.remove();
                dropzoneEl.classList.remove("invisible");
                this.onDropZoneOut();
            },
            onDragEnd: ({ x, y, helper, dropzone }) => {
                // Undo the preview if any.
                this.cancelSnippetPreview?.();

                this.document.body.classList.remove("oe_dropzone_active");
                snippetEl.remove();
                let currentDropzoneEl = dropzone && dropzone.el;

                // If the snippet was dropped outside of a dropzone, find the
                // dropzone that is the nearest to the dropping point.
                if (!currentDropzoneEl) {
                    const blockTabLeft = this.blockTabRef.el.getBoundingClientRect().left;
                    if (y > 3 && x + helper.getBoundingClientRect().height < blockTabLeft) {
                        const closestDropzoneEl = closest(dropzoneEls, { x, y });
                        if (closestDropzoneEl) {
                            currentDropzoneEl = closestDropzoneEl;
                        }
                    } else {
                        this.cancelDragAndDrop();
                    }
                }

                if (currentDropzoneEl) {
                    currentDropzoneEl.after(snippetEl);
                    this.shared.dropzone.removeDropzones();

                    if (!isSnippetGroup) {
                        this.processDroppedSnippet(snippetEl);
                    } else {
                        this.shared.operation.next(
                            async () => {
                                await this.onSnippetGroupDrop(snippet, snippetEl);
                            },
                            { withLoadingEffect: false }
                        );
                    }
                }

                this.state.ongoingInsertion = false;
                this.onDropZoneStop(); // TODO check if it is the best place.
                delete this.cancelSnippetPreview;
                if (!isSnippetGroup) {
                    delete this.cancelDragAndDrop;
                }
                dragAndDropResolve();
            },
        };

        this.draggableComponent = useDragAndDrop(dragAndDropOptions);
    }

    /**
     *
     * @param {HTMLElement} snippetEl
     */
    async processDroppedSnippet(snippetEl) {
        this.updateDroppedSnippet(snippetEl);
        // TODO Fix in modal,... => use web_editor scrollTo so we have extra
        // offset + scrollable
        scrollToWindow(snippetEl, { behavior: "smooth", offset: 50 });
        // Build the snippet.
        for (const onSnippetDropped of this.resources["on_snippet_dropped_handlers"] || []) {
            const cancel = await onSnippetDropped({ snippetEl });
            // Cancel everything if the resource asked to.
            if (cancel) {
                this.cancelDragAndDrop?.();
                return;
            }
        }
        this.env.editor.config.updateInvisibleElementsPanel();
        this.shared.disableSnippets.disableUndroppableSnippets();
        this.env.editor.shared.history.addStep();
    }

    /**
     * Update the dropped snippet to build & adapt dynamic content right
     * after adding it to the DOM.
     *
     * @param {HTMLElement} snippetEl
     */
    updateDroppedSnippet(snippetEl) {
        // If the snippet is "drop in only", remove the attributes that make it
        // a draggable snippet, so it becomes a simple HTML code.
        if (snippetEl.classList.contains("o_snippet_drop_in_only")) {
            snippetEl.classList.remove("o_snippet_drop_in_only");
            delete snippetEl.dataset.snippet;
            delete snippetEl.dataset.name;
        }
    }

    /**
     * Hooks allowing other modules to react to drop zones being enabled.
     */
    onDropzoneStart() {}
    onDropZoneOver() {}
    onDropZoneOut() {}
    onDropZoneStop() {}
}
