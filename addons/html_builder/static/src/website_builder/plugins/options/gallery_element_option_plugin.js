import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

export class GalleryElementOptionPlugin extends Plugin {
    static id = "galleryElementOption";

    resources = {
        builder_options: [
            withSequence(20, {
                template: "html_builder.GalleryElementOption",
                selector:
                    ".s_image_gallery img, .s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setGalleryElementPosition: {
                apply: ({ editingElement, value: position }) => {
                    const carouselOptionName =
                        editingElement.parentNode.parentNode.classList.contains("s_carousel_intro")
                            ? "CarouselIntro"
                            : "Carousel";
                    const optionName = editingElement.classList.contains("carousel-item")
                        ? carouselOptionName
                        : "GalleryImageList";

                    // Carousel and gallery image list are both managed by the same handler
                    // remember to implement the handler for carousel when it's created
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
