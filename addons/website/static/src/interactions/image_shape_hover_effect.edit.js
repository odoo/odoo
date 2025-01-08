import { ImageShapeHoverEffect } from "./image_shape_hover_effect";
import { registry } from "@web/core/registry";

const ImageShapeHoverEffectEdit = I => class extends I {
    adjustImageSourceFrom(preloadedImageEl) {
        if (!this.el.dataset.originalSrcBeforeHover) {
            this.el.dataset.originalSrcBeforeHover = this.originalImgSrc;
        }
        super.adjustImageSourceFrom(preloadedImageEl);
    }
};

registry
    .category("public.interactions.edit")
    .add("website.image_shape_hover_effect", {
        Interaction: ImageShapeHoverEffect,
        mixin: ImageShapeHoverEffectEdit,
    });
