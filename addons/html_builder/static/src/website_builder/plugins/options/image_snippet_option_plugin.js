import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ImageSnippetOptionPlugin extends Plugin {
    static id = "imageSnippetOption";
    static dependencies = ["media"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(".s_image")) {
            return;
        }

        // Open the media dialog and replace the image snippet placeholder by
        // the selected image.
        let isImageSelected = false;
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: true,
                save: (selectedImageEl) => {
                    isImageSelected = true;
                    snippetEl.replaceWith(selectedImageEl);
                },
            });
            onClose.then(() => {
                // If no image was selected, remove the placeholder.
                if (!isImageSelected) {
                    snippetEl.remove();
                }
                resolve();
            });
        });

        return !isImageSelected;
    }
}

registry.category("website-plugins").add(ImageSnippetOptionPlugin.id, ImageSnippetOptionPlugin);
