/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Parallax } from "@website/interactions/parallax/parallax";

const log = makeLogger("website.interaction.parallax.preview");

const ParallaxPreview = (I) =>
    class extends I {
        PARALLAX_RATE = 16;
        SCALE = 2.4;
        dynamicContent = {};

        setup() {
            this.backgroundEl = this.el.querySelector(".s_parallax_bg");
            this.previewContainerEl = this.el.ownerDocument.body;
            this.speed =
                parseFloat(this.el.getAttribute("data-scroll-background-ratio")) || 0;
            this.isZoomIn = this.el.dataset.parallaxType === "zoomIn";
            this.isZoomOut = this.el.dataset.parallaxType === "zoomOut";
            this.isZoom = this.isZoomIn || this.isZoomOut;
            this.baseScale = this.isZoom ? 1 : this.SCALE;
            log.lifecycle("ParallaxPreview setup", () => ({
                speed: this.speed,
                isZoomIn: this.isZoomIn,
                isZoomOut: this.isZoomOut,
            }));
        }

        start() {
            if (!this.backgroundEl || !this.previewContainerEl) {
                log.logic("ParallaxPreview start: missing element, skip", () => ({
                    hasBackground: !!this.backgroundEl,
                    hasPreviewContainer: !!this.previewContainerEl,
                }));
                return;
            }

            this.applyInitialStyles();
            this.initializeIntersectionObserver();
        }

        destroy() {
            this.previewContainerEl?.removeEventListener(
                "scroll",
                this.updateParallaxPosition,
            );
            if (this.observer) {
                this.observer.disconnect();
                this.observer = null;
                log.lifecycle("ParallaxPreview destroy: observer disconnected");
            }
        }

        applyInitialStyles() {
            this.el.style.overflow = "hidden";

            Object.assign(this.backgroundEl.style, {
                width: "100%",
                height: "100%",
                left: "-50%",
                top: "-50%",
                backgroundPosition: "center bottom",
                transform: `translate(50%, 50%) scale(${this.baseScale})`,
                willChange: "transform",
            });
        }

        initializeIntersectionObserver() {
            this.observer = new IntersectionObserver(
                this.bindDeferred((entries) => {
                    if (this.isDestroyed) {
                        return;
                    }
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            log.lifecycle(
                                "ParallaxPreview visible: scroll listener added",
                            );
                            this.updateParallaxPosition();
                            this.previewContainerEl.addEventListener(
                                "scroll",
                                this.updateParallaxPosition,
                            );
                        } else {
                            log.lifecycle(
                                "ParallaxPreview hidden: scroll listener removed",
                            );
                            this.previewContainerEl.removeEventListener(
                                "scroll",
                                this.updateParallaxPosition,
                            );
                        }
                    });
                }),
            );

            this.observer.observe(this.el);
        }

        updateParallaxPosition = () => {
            const clamp = (value) => Math.min(1, Math.max(0, value));
            const rect = this.el.getBoundingClientRect();
            const viewportHeight = this.previewContainerEl.clientHeight;
            const relativeScrollProgress = viewportHeight
                ? rect.top / viewportHeight
                : 0;

            const parallaxShift = relativeScrollProgress * this.PARALLAX_RATE * 100;
            let scale = this.baseScale;
            let translateY = `calc(50% - ${parallaxShift}px)`;
            if (this.isZoom) {
                const minScrollPos = -rect.height;
                const maxScrollPos = viewportHeight;
                const scrollRange = maxScrollPos - minScrollPos;
                const progress = scrollRange
                    ? clamp((rect.top - minScrollPos) / scrollRange)
                    : 0;
                const zoomProgress = this.isZoomIn
                    ? Math.min(1, progress * 2.5)
                    : progress;
                const maxZoom = this.speed + 1;
                const zoomScale = this.isZoomOut
                    ? 1 + (maxZoom - 1) * zoomProgress
                    : maxZoom - (maxZoom - 1) * zoomProgress;
                scale *= zoomScale;
                translateY = "50%";
            }
            this.backgroundEl.style.transform = `translate(50%, ${translateY}) scale(${scale})`;
        };
    };

registry.category("public.interactions.preview").add("website.parallax", {
    Interaction: Parallax,
    mixin: ParallaxPreview,
});
