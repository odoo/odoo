import { registry } from "@web/core/registry";
import { ImageShapeHoverEffect } from "./image_shape_hover_effect";

const ImageShapeHoverEffectEdit = (I) =>
    class extends I {
        destroy() {
            // The originalImgSrc might not yet be updated by sourceObserver
            // if the interaction stops in the same tick as the mutation
            // happens. Only restore the src if it still matches the last
            // hovering src.
            if (this.el.src === this.hoveringImgSrc) {
                this.el.src = this.originalImgSrc;
            }
            this.disconnectSourceObserver();
        }

        // Copy of the mouseLeave of the original interaction. The only
        // difference is that it restores the original image source after the
        // animation is over, since in edit mode the image source might change
        // before the end of the animation (for example while previewing shapes
        // image filters or something else).
        mouseLeave() {
            this.lastMouseEvent = this.lastMouseEvent.then(
                () =>
                    new Promise((resolve) => {
                        if (!this.originalImgSrc || !this.svgInEl || !this.el.dataset.hoverEffect) {
                            resolve();
                            return;
                        }
                        if (!this.svgOutEl) {
                            // Reverse animations.
                            this.svgOutEl = this.svgInEl.cloneNode(true);
                            const animateTransformEls = this.svgOutEl.querySelectorAll(
                                "#hoverEffects animateTransform, #hoverEffects animate"
                            );
                            animateTransformEls.forEach((animateTransformEl) => {
                                let valuesValue = animateTransformEl.getAttribute("values");
                                valuesValue = valuesValue.split(";").reverse().join(";");
                                animateTransformEl.setAttribute("values", valuesValue);
                            });
                        }
                        this.setImgSrc(this.svgOutEl, () => {
                            // After the animation, restore original src
                            setTimeout(() => {
                                if (this.isDestroyed) {
                                    resolve();
                                    return;
                                }
                                this.disconnectSourceObserver();
                                this.el.src = this.originalImgSrc;
                                this.connectSourceObserver();
                                this.el.onload = () => {
                                    resolve();
                                };
                            }, this.getAnimationMaxDuration(this.svgOutEl));
                        });
                    })
            );
        }

        // returns the time after which the animation should be over
        getAnimationMaxDuration(svg) {
            let maxDuration = 0;
            const animateEls = svg.querySelectorAll(
                "#hoverEffects animateTransform, #hoverEffects animate"
            );
            animateEls.forEach((animateEl) => {
                const dur = animateEl.getAttribute("dur");
                if (dur) {
                    const duration = parseFloat(dur) * (dur.endsWith("ms") ? 1 : 1000);
                    maxDuration = Math.max(maxDuration, duration);
                }
            });
            return maxDuration;
        }
    };

registry.category("public.interactions.edit").add("website.image_shape_hover_effect", {
    Interaction: ImageShapeHoverEffect,
    mixin: ImageShapeHoverEffectEdit,
});
