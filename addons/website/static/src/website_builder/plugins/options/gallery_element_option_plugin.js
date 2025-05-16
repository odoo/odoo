import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";

export class GalleryElementOptionPlugin extends Plugin {
    static id = "galleryElementOption";

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                template: "html_builder.GalleryElementOption",
                selector:
                    ".s_image_gallery img, .s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setGalleryElementPosition: {
                apply: ({ editingElement, value: position }) => {
                    const optionName = editingElement.classList.contains("carousel-item")
                        ? "Carousel"
                        : "GalleryImageList";

                    // Carousel and gallery image list are both managed by the same handler
                    this.dispatchTo("on_reorder_items_handlers", {
                        elementToReorder: editingElement,
                        position: position,
                        optionName: optionName,
                    });
                },
            },
        };
    }
}

registry.category("website-plugins").add(GalleryElementOptionPlugin.id, GalleryElementOptionPlugin);
