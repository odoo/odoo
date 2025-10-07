import { registry } from "@web/core/registry";
import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";

export class CarouselMultiple extends CarouselSlider {
    static selector = ".s_carousel_multiple";
    static dependencies = ["carouselOption"];

    dynamicContent = {
        _window: { "t-on-resize": this.debounced(this.onResize, 100) },
        _root: {
            "t-on-click": this.onClick,
            "t-on-slid.bs.carousel": this.onSlidCarousel,
        },
    };
    start() {
        super.start();
        this.displayedSlidesCount = Number(getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items"));
        this.itemsLength = this.el.querySelectorAll(".carousel-item").length;
    }

    onSlidCarousel(event) {
        super.onSlidCarousel();
        if (event.to >= this.itemsLength - this.displayedSlidesCount + 1) {
            // When we are to the last slide and we click to next
            window.Carousel.getOrCreateInstance(this.el).to(0);
        }
        if (event.to === this.itemsLength - 1 && event.direction === "right") {
            // When we are at the first slide and we click to previous slide : go to the last one
            window.Carousel.getOrCreateInstance(this.el).to(this.itemsLength - this.displayedSlidesCount);
        }
        this.carouselInnerEl.style.transform = "translateX(calc(((100% - (var(--o-carousel-multiple-items-gap) * (var(--o-carousel-multiple-items) - 1))) / var(--o-carousel-multiple-items) + var(--o-carousel-multiple-items-gap)) * "+ event.to +" * -1)";
    };

    onResize() {
        const currentDisplaySlides = Number(getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items"));
        if(this.env.isSmall) {
            this.carouselInnerEl.removeAttribute('style');
        } else if (currentDisplaySlides !== this.displayedSlidesCount) {
            // Reset the slider when the number of displayed slides changes.
            window.Carousel.getOrCreateInstance(this.el).to(0);
        }
        this.displayedSlidesCount = currentDisplaySlides;
    }

    // Only used in carousel_multiple.edit.js
    onClick() {}
}

registry
    .category("public.interactions")
    .add("website.carousel_multiple", CarouselMultiple);
