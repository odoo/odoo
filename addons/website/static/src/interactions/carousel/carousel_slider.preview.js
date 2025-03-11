import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderPreview = (I) =>
    class extends I {
        carouselOptions = { ride: true, pause: true, interval: 500 };

        setup() {
            // Bind mouse events to the entire section (top-most parent of the
            // snippet). This ensures events trigger when hovering anywhere on
            // the snippet, even if the carousel itself is smaller in width.
            if (this.el.tagName === "SECTION") {
                this.carouselSnippetEl = this.el;
            } else {
                this.carouselSnippetEl = this.el.closest("section");
            }
        }

        start() {
            super.start();

            this.carouselSnippetEl.style.pointerEvents = "auto";

            this.addListener(this.carouselSnippetEl, "mouseenter", this.mouseEnter);
            this.addListener(this.carouselSnippetEl, "mouseleave", this.mouseLeave);
        }

        /**
         * Starts the carousel autoplay when the mouse enters the element.
         */
        mouseEnter = () => {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            carousel.cycle();
        };

        /**
         * Pauses the carousel and resets it to the first slide when the mouse
         * leaves the element.
         */
        mouseLeave = () => {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            carousel.pause();
            carousel.to(0);
        };
    };

registry.category("public.interactions.preview").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderPreview,
});
