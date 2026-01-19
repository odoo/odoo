import { Parallax } from "@website/interactions/parallax/parallax";
import { registry } from "@web/core/registry";

// A manual parallax implementation is required for snippet previews because
// snippets are scaled down in preview, and `background-attachment: fixed`
// (which enables the native parallax effect) does not work on transformed
// elements.
//
// To simulate parallax behavior, we manually adjust the background position
// relative to the scroll position.

const ParallaxPreview = (I) =>
    class extends I {
        // The PARALLAX_RATE controls how fast the background moves.
        // A higher PARALLAX_RATE means faster movement, which requires a larger
        // background SCALE to prevent background cutoff.
        PARALLAX_RATE = 16;
        SCALE = 2.4;
        dynamicContent = {};

        setup() {
            this.backgroundEl = this.el.querySelector(".s_parallax_bg");
            this.previewContainerEl = this.el.ownerDocument.body;
            this.speed = parseFloat(this.el.getAttribute("data-scroll-background-ratio")) || 0;
            this.isZoomIn = this.el.dataset.parallaxType === "zoomIn";
            this.isZoomOut = this.el.dataset.parallaxType === "zoomOut";
            this.isZoom = this.isZoomIn || this.isZoomOut;
            this.baseScale = this.isZoom ? 1 : this.SCALE;
        }

        start() {
            if (!this.backgroundEl || !this.previewContainerEl) {
                return;
            }

            this.applyInitialStyles();
            this.initializeIntersectionObserver();
        }

        destroy() {
            if (this.observer) {
                this.observer.disconnect();
                this.observer = null;
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

        /**
         * Sets up an IntersectionObserver to detect when the element enters
         * or leaves the viewport, ensuring the parallax effect is applied
         * only when necessary.
         */
        initializeIntersectionObserver() {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.updateParallaxPosition();
                        this.previewContainerEl.addEventListener(
                            "scroll",
                            this.updateParallaxPosition
                        );
                    } else {
                        this.previewContainerEl.removeEventListener(
                            "scroll",
                            this.updateParallaxPosition
                        );
                    }
                });
            });

            this.observer.observe(this.el);
        }

        /**
         * Updates the background position to create a parallax effect based on
         * scroll position.
         */
        updateParallaxPosition = () => {
            const clamp = (value) => Math.min(1, Math.max(0, value));
            const rect = this.el.getBoundingClientRect();
            const viewportHeight = this.previewContainerEl.clientHeight;
            const relativeScrollProgress = viewportHeight ? rect.top / viewportHeight : 0;

            const parallaxShift = relativeScrollProgress * this.PARALLAX_RATE * 100;
            let scale = this.baseScale;
            let translateY = `calc(50% - ${parallaxShift}px)`;
            if (this.isZoom) {
                const minScrollPos = -rect.height;
                const maxScrollPos = viewportHeight;
                const scrollRange = maxScrollPos - minScrollPos;
                const progress = scrollRange ? clamp((rect.top - minScrollPos) / scrollRange) : 0;
                const zoomProgress = this.isZoomIn ? Math.min(1, progress * 2.5) : progress;
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
