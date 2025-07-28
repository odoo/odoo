import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class GalleryElementOption extends BaseOptionComponent {
    static template = "website.GalleryElementOption";
    static selector =
        ".s_image_gallery img, .s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item";
}

export class GalleryElementOptionPlugin extends Plugin {
    static id = "galleryElementOption";

    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC, GalleryElementOption)],
        builder_actions: {
            SetGalleryElementPositionAction,
        },
    };
}

export class SetGalleryElementPositionAction extends BuilderAction {
    static id = "setGalleryElementPosition";
    apply({ editingElement: activeItemEl, value: position }) {
        const optionName = activeItemEl.classList.contains("carousel-item")
            ? "Carousel"
            : "GalleryImageList";

        // Get the items to reorder.
        const itemEls = [];
        for (const getGalleryItems of this.getResource("get_gallery_items_handlers")) {
            itemEls.push(...getGalleryItems(activeItemEl, optionName));
        }

        // Reorder the items.
        const oldPosition = itemEls.indexOf(activeItemEl);
        if (oldPosition === 0 && position === "prev") {
            position = "last";
        } else if (oldPosition === itemEls.length - 1 && position === "next") {
            position = "first";
        }
        itemEls.splice(oldPosition, 1);
        switch (position) {
            case "first":
                itemEls.unshift(activeItemEl);
                break;
            case "prev":
                itemEls.splice(Math.max(oldPosition - 1, 0), 0, activeItemEl);
                break;
            case "next":
                itemEls.splice(oldPosition + 1, 0, activeItemEl);
                break;
            case "last":
                itemEls.push(activeItemEl);
                break;
        }

        // Update the DOM with the new items order.
        this.dispatchTo("reorder_items_handlers", activeItemEl, itemEls, optionName);
    }
}

registry.category("website-plugins").add(GalleryElementOptionPlugin.id, GalleryElementOptionPlugin);
