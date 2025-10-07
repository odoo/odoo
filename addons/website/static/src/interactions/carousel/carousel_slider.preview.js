import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderPreview = (I) =>
    class extends I {
        carouselOptions = { ride: true, pause: true, interval: 500 };

        dynamicSelectors = {
            ...this.dynamicSelectors,
            _snippetPreviewWrapEl: () => this.el.closest(".o_snippet_preview_wrap"),
        };
        dynamicContent = {
            ...this.dynamicContent,
            // Bind events to the entire preview wrap. This ensures events
            // trigger when hovering anywhere on the snippet, even though the
            // preview containers are `inert`.
            _snippetPreviewWrapEl: {
                "t-on-mouseenter": this.mouseEnter,
                "t-on-mouseleave": this.mouseLeave,
                "t-on-focusin": this.mouseEnter,
                "t-on-focusout": this.mouseLeave,
            },
        };

        /**
         * Starts the carousel autoplay when the mouse enters the element.
         */
        mouseEnter() {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            const isMultipleCarousel = this.el.classList.contains("s_carousel_multiple");
            const carouselInnerEl = this.el.querySelector(".carousel-inner");
            const slidesElts = this.el.querySelectorAll(".carousel-item");
            if (isMultipleCarousel) {
                this.el.addEventListener("slid.bs.carousel", (event) => {
                    const slideActive = this.el.querySelector(".carousel-item.active");
                    const currentIndex = slideActive
                        ? Array.from(slidesElts).indexOf(slideActive)
                        : -1;
                    const displayedSlides = Number(
                        getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items")
                    );
                    if (currentIndex >= slidesElts.length - displayedSlides) {
                        carousel.to(0);
                    }
                    carouselInnerEl.style.transform =
                        "translateX(calc(((100% - (var(--o-carousel-multiple-items-gap) * (var(--o-carousel-multiple-items) - 1))) / var(--o-carousel-multiple-items) + var(--o-carousel-multiple-items-gap)) * " +
                        event.to +
                        " * -1)";
                });
            }
            carousel.cycle();
        }

        /**
         * Pauses the carousel and resets it to the first slide when the mouse
         * leaves the element.
         */
        mouseLeave() {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            carousel.pause();
            carousel.to(0);
        }
    };

registry.category("public.interactions.preview").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderPreview,
});
