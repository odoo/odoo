import { scrollTo } from "@html_builder/utils/scrolling";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { closest } from "@web/core/utils/ui";

/**
 * @typedef {import("@html_builder/core/drag_and_drop_plugin").DragState} DragState
 */

export class BlockTabPlugin extends Plugin {
    static id = "blockTab";
    static dependencies = ["operation", "history", "dropzone", "disableSnippets"];
    static shared = ["insertSnippetGroup", "scrollToDroppedSnippet", "processDroppedSnippet"];

    /**
     * Opens and manages the snippet dialog after clicking on a snippet group,
     * and inserts the selected snippet in the page.
     *
     * @param {Object} snippet the clicked snippet group
     */
    insertSnippetGroup(snippet) {
        this.dependencies.operation.next(
            async () => {
                const cancelInsertion = this.dependencies.history.makeSavePoint();
                let snippetEl;
                await new Promise((resolve) => {
                    this.config.snippetModel.openSnippetDialog(
                        snippet,
                        {
                            onSelect: (snippet) => {
                                snippetEl = snippet.content.cloneNode(true);

                                // Add the dropzones corresponding to a section and
                                // make them invisible.
                                const selectors =
                                    this.dependencies.dropzone.getSelectors(snippetEl);
                                let dropzoneEls =
                                    this.dependencies.dropzone.activateDropzones(selectors);

                                // If no dropzone is left after the filter, then
                                // allow the drop by click inside [data-snippet]
                                // elements
                                const filteredDropzoneEls = dropzoneEls.filter(
                                    (dropzoneEl) =>
                                        !dropzoneEl.closest("[data-snippet]:not(:has(> .modal))")
                                );
                                dropzoneEls = filteredDropzoneEls.length
                                    ? filteredDropzoneEls
                                    : dropzoneEls;

                                this.editable
                                    .querySelectorAll(".oe_drop_zone")
                                    .forEach((dropzoneEl) => dropzoneEl.classList.add("invisible"));

                                // Find the dropzone closest to the center of the
                                // viewport and not located in the top quarter of
                                // the viewport.
                                const iframeWindow = this.document.defaultView;
                                const viewPortCenterPoint = {
                                    x: iframeWindow.innerWidth / 2,
                                    y: iframeWindow.innerHeight / 2,
                                };
                                const validDropzoneEls = dropzoneEls.filter(
                                    (el) =>
                                        el.getBoundingClientRect().top >= viewPortCenterPoint.y / 2
                                );
                                const closestDropzoneEl =
                                    closest(validDropzoneEls, viewPortCenterPoint) ||
                                    dropzoneEls.at(-1);

                                // Insert the selected snippet.
                                closestDropzoneEl.after(snippetEl);
                                this.dependencies.dropzone.removeDropzones();
                                return snippetEl;
                            },
                            onClose: () => {
                                resolve();
                            },
                        },
                        this
                    );
                });

                if (snippetEl) {
                    await this.scrollToDroppedSnippet(snippetEl);
                    await this.processDroppedSnippet(snippetEl, cancelInsertion);
                }
            },
            {
                withLoadingEffect: false,
                shouldInterceptClick: true,
                canTimeout: false,
            }
        );
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
            if (snippetEl.classList.length === 0) {
                snippetEl.removeAttribute("class");
            }
            delete snippetEl.dataset.snippet;
            delete snippetEl.dataset.name;
        }
    }

    /**
     * @param {HTMLElement} snippetEl
     * @param {Function} cancelInsertion
     * @param {DragState} [dragState]
     */
    async processDroppedSnippet(snippetEl, cancelInsertion, dragState = {}) {
        this.updateDroppedSnippet(snippetEl);
        // Build the snippet.
        for (const onSnippetDropped of this.getResource("on_snippet_dropped_handlers")) {
            const cancel = await onSnippetDropped({ snippetEl, dragState });
            // Cancel everything if the resource asked to.
            if (cancel) {
                cancelInsertion();
                return;
            }
            // Update `snippetEl` (and `draggedEl` of `dragState`) if it was
            // replaced in the handler.
            if (dragState.replacedSnippetEl) {
                if (dragState.draggedEl === snippetEl) {
                    dragState.draggedEl = dragState.replacedSnippetEl;
                }
                snippetEl = dragState.replacedSnippetEl;
                delete dragState.replacedSnippetEl;
            }
        }
        this.config.updateInvisibleElementsPanel();
        this.dependencies.disableSnippets.disableUndroppableSnippets();
        this.dependencies.history.addStep();
    }

    /**
     * Scroll to the dropped snippet and leave a space of 50px above to show
     * what is above. If the snippet takes 100% of the screen height, we show it
     * by not having an extra offset above it.
     *
     * @param {HTMLElement} snippetEl
     */
    async scrollToDroppedSnippet(snippetEl) {
        const isFullScreenHeight = snippetEl.matches(".o_full_screen_height");
        await scrollTo(snippetEl, { extraOffset: isFullScreenHeight ? 0 : 50 });
    }
}

registry.category("builder-plugins").add(BlockTabPlugin.id, BlockTabPlugin);
