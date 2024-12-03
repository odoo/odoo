import { registry } from "@web/core/registry";
import { ImageShapeHoverEffect } from "./image_shape_hover_effect";

export class ImageShapeHoverEffectEdit extends ImageShapeHoverEffect {
    /**
     * @override
     */
    adjustImageSourceFrom(preloadedImageEl) {
        // TODO Handle edit mode
        // this.options.wysiwyg.odooEditor.observerUnactive("setImgHoverEffectSrc");
        if (!this.el.dataset.originalSrcBeforeHover) {
            this.el.dataset.originalSrcBeforeHover = this.originalImgSrc;
        }
        super.adjustImageSourceFrom(preloadedImageEl);
        // TODO Handle edit mode
        // this.options.wysiwyg.odooEditor.observerActive("setImgHoverEffectSrc");
    }
}

registry
    .category("website.edit_active_elements")
    .add("website.image_shape_hover_effect", ImageShapeHoverEffectEdit);
