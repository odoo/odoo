import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Parallax extends Interaction {
    static selector = ".parallax";
    dynamicSelectors = Object.assign(this.dynamicSelectors, {
        _modal: () => this.el.closest(".modal"),
        _bg: () => this.el.querySelector(":scope > .s_parallax_bg"),
    });
    dynamicContent = {
        _document: { "t-on-scroll": this.onScroll },
        _window: { "t-on-resize": this.updateBackgroundHeight },
        _modal: { "t-on-shown.bs.modal": this.updateBackgroundHeight },
        _bg: {
            "t-att-style": () => ({
                top: this.styleTop,
                bottom: this.styleBottom,
                transform: this.styleTransform,
            }),
        },
    };

    setup() {
        this.speed = 0;
        this.ratio = 0;
        this.viewportHeight = 0;
        this.parallaxHeight = 0;
        this.minScrollPos = 0;
        this.maxScrollPos = 0;

        this.styleTop = undefined;
        this.styleBottom = undefined;
        this.styleTransform = undefined;
        this.isZoomIn = undefined;
        this.isZoomOut = undefined;
    }

    start() {
        if (this.el.classList.contains("carousel-item")) {
            // CarouselSlider.computeMaxHeight() sets a stable min-height on all
            // carousel items in its own start(), which may run after this one.
            // Wait one frame so that min-height is in place before we take our
            // initial measurement. This ensures the height used here equals the
            // height used after any animation completes, preventing a snap on
            // the very first animation.
            this.waitForAnimationFrame(() => {
                this.updateBackgroundHeight();
            });
        } else {
            this.updateBackgroundHeight();
            this.updateContent();
        }
    }

    updateBackgroundHeight() {
        this.speed = parseFloat(this.el.getAttribute("data-scroll-background-ratio")) || 0;
        if (this.speed === 0 || this.speed === 1) {
            return;
        }
        this.viewportHeight = document.body.clientHeight;
        const targetEl = this.el.classList.contains("carousel-item")
            ? this.el.parentElement
            : this.el;
        this.parallaxHeight = targetEl.getBoundingClientRect().height;

        // The parallax is in the viewport if it is between these two values
        // min : bottom of the parallax in at the top of the page
        // max : top of the parallax in at the bottom of the page
        this.minScrollPos = -this.parallaxHeight;
        this.maxScrollPos = this.viewportHeight;

        this.ratio = this.speed * (this.viewportHeight / 10);

        this.styleTop = -Math.abs(this.ratio) + "px";
        this.styleBottom = -Math.abs(this.ratio) + "px";

        const parallaxType = this.el.dataset.parallaxType;
        // Compatibility: Previously, "zoom_out" and "zoom_in" had their
        // behavior reversed. The previous "zoom_out" correspond to the
        // current "zoomIn" type.
        this.isZoomIn = parallaxType === "zoomIn" || parallaxType === "zoom_out";
        this.isZoomOut = parallaxType === "zoomOut" || parallaxType === "zoom_in";

        this.onScroll();
    }

    onScroll() {
        const targetEl = this.el.classList.contains("carousel-item")
            ? this.el.parentElement
            : this.el;
        const currentPosition = targetEl.getBoundingClientRect().height;
        if (
            this.speed === 0 ||
            this.speed === 1 ||
            currentPosition < this.minScrollPos ||
            currentPosition > this.maxScrollPos
        ) {
            return;
        }
        // Calculate progress based on the element's visible range
        const scrollRange = this.maxScrollPos - this.minScrollPos;
        const progress = Math.min(
            1,
            Math.max(0, (currentPosition - this.minScrollPos) / scrollRange)
        );

        if (this.isZoomOut) {
            const initialZoom = 1;
            const maxZoom = this.speed + 1;

            this.styleTransform = `scale(${initialZoom + (maxZoom - initialZoom) * progress})`;
        } else if (this.isZoomIn) {
            const initialZoom = this.speed + 1;

            this.styleTransform = `scale(${initialZoom - (initialZoom - 1) * progress})`;
        } else {
            const r = 1 / (this.minScrollPos - this.maxScrollPos);
            const offset = 1 - 2 * this.minScrollPos * r;
            const movement = -Math.round(this.ratio * (r * currentPosition + offset));

            this.styleTransform = "translateY(" + movement + "px)";
        }
    }
}

registry.category("public.interactions").add("website.parallax", Parallax);

registry.category("public.interactions.edit").add("website.parallax", {
    Interaction: Parallax,
});
