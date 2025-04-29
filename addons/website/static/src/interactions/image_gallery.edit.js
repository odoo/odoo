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
        this.renderAt("website.empty_image_gallery_alert", {}, this.el);
    }
    onAddImage() {
        const applySpec = { editingElement: this.el };
        this.services["website_edit"].applyAction("addImage", applySpec);
    }
}

registry.category("public.interactions.edit").add("website.image_gallery_edit", {
    Interaction: ImageGalleryEdit,
});
