import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ImageSnippetOptionPlugin extends Plugin {
    static id = "imageSnippetOption";
    static dependencies = ["media"];
    static shared = ["onSnippetDropped"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        so_content_addition_selectors: [".s_image"],
    };

    async onSnippetDropped({ snippetEl, dragState }) {
        if (!snippetEl.matches(".s_image")) {
            return;
        }

        let discardSnippet = false;
        // Open the media dialog and replace the image snippet placeholder by
        // the selected image.
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog(
                this.getMediaDialogProps(snippetEl, dragState)
            );
            onClose.then((closeParams) => {
                discardSnippet = this.onCloseMediaDialog({ closeParams, snippetEl, dragState });
                resolve();
            });
        });
        return discardSnippet;
    }

    getMediaDialogProps(snippetEl, dragState) {
        return {
            onlyImages: true,
            save: async (...args) => {
                const selectedImageEl = args[0];
                const elementToReplace = args[3] || snippetEl;
                elementToReplace.replaceWith(selectedImageEl);
                // If the "Image" snippet was dropped as a grid item, make
                // it a grid image.
                if (dragState.draggedEl.classList.contains("o_grid_item")) {
                    dragState.draggedEl.classList.add("o_grid_item_image");
                }
                dragState.replacedSnippetEl = selectedImageEl;
            },
        };
    }

    onCloseMediaDialog({ closeParams, snippetEl, dragState }) {
        return closeParams.closeReason !== "save";
    }
}

registry.category("builder-plugins").add(ImageSnippetOptionPlugin.id, ImageSnippetOptionPlugin);
