import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ImageGalleryEdit extends Interaction {
    static selector = ".s_image_gallery";
    dynamicContent = {
        ".o_empty_gallery_alert": {
            "t-on-click": this.onAddImage.bind(this),
        },
    };
    setup() {
        const containerEl = this.el.querySelector(
            ".container, .container-fluid, .o_container_small"
        );
        this.renderAt("html_builder.empty_image_gallery_alert", {}, containerEl);
    }
    onAddImage() {
        const applySpec = { editingElement: this.el };
        this.services["website_edit"].applyAction("addImage", applySpec);
    }
}

registry.category("public.interactions.edit").add("html_builder.image_gallery_edit", {
    Interaction: ImageGalleryEdit,
});
