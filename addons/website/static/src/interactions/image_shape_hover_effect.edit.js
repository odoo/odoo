/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { ImageShapeHoverEffect } from "@website/interactions/image_shape_hover_effect";

const log = makeLogger("website.interaction.image_shape_hover_effect.edit");

const ImageShapeHoverEffectEdit = (I) =>
    class extends I {
        afterMouseLeave(svg, version) {
            return new Promise((resolve) => {
                const cancel = () => {
                    clearTimeout(timer);
                    forgetCleanup();
                    if (this.cancelPendingHover === cancel) {
                        this.cancelPendingHover = null;
                    }
                    resolve();
                };
                const timer = setTimeout(() => {
                    this.flushSourceChanges();
                    forgetCleanup();
                    if (this.cancelPendingHover === cancel) {
                        this.cancelPendingHover = null;
                    }
                    if (this.isDestroyed || version !== this.sourceVersion) {
                        resolve();
                        return;
                    }
                    log.lifecycle("ImageShapeHoverEffectEdit restore original source");
                    this.setImageSource(this.originalImgSrc, resolve);
                }, this.getAnimationMaxDuration(svg));
                const forgetCleanup = this.registerCleanup(cancel);
                this.cancelPendingHover = cancel;
            });
        }

        getAnimationMaxDuration(svg) {
            let maxDuration = 0;
            const animateEls = svg.querySelectorAll(
                "#hoverEffects animateTransform, #hoverEffects animate",
            );
            animateEls.forEach((animateEl) => {
                const dur = animateEl.getAttribute("dur");
                if (dur) {
                    const duration = parseFloat(dur) * (dur.endsWith("ms") ? 1 : 1000);
                    if (Number.isFinite(duration)) {
                        maxDuration = Math.max(maxDuration, duration);
                    }
                }
            });
            return maxDuration;
        }
    };

registry.category("public.interactions.edit").add("website.image_shape_hover_effect", {
    Interaction: ImageShapeHoverEffect,
    mixin: ImageShapeHoverEffectEdit,
});
