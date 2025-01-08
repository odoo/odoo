import { registry } from "@web/core/registry";
import { ImageShapeHoverEffect } from "./image_shape_hover_effect";

const ImageShapeHoverEffectEdit = I => class extends I {
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
};

registry
    .category("public.interactions.edit")
    .add("website.image_shape_hover_effect", {
        Interaction: ImageShapeHoverEffect,
        mixin: ImageShapeHoverEffectEdit,
    });