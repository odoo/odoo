import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CarouselSlider extends Interaction {
    static selector = ".carousel";
    dynamicContent = {
        "img": {
            "t-on-load": this.computeMaxHeight,
        },
        _window: {
            "t-on-resize": this.debounced(this.computeMaxHeight, 250),
        },
        ".carousel-item": {
            "t-att-style": () => ({
                "min-height": `${this.maxHeight}px`,
            }),
        },
    };
    carouselOptions = undefined;
    OLD_AUTO_SLIDING_SNIPPETS = ["s_image_gallery"];
    setup() {
        this.maxHeight = undefined;
        this.hasInterval = ![undefined, "false", "0"].includes(this.el.dataset.bsInterval);
        if (!this.hasInterval || !this.el.dataset.bsRide) {
            //if bsInterval 0 or false or undefined means no auto slide
            this.el.dataset.bsRide = "noAutoSlide";
        } else if (this.hasInterval && this.el.dataset.bsRide === "noAutoSlide") {
            //if bsInterval is set and bsRide is noAutoSlide, then we need to set it to true
            //except for the OLD_AUTO_SLIDING_SNIPPETS where we need to set it to carousel
            const snippetName = this.el.closest("[data-snippet]")?.dataset.snippet;
            this.el.dataset.bsRide = this.OLD_AUTO_SLIDING_SNIPPETS.includes(snippetName) ? "carousel" : "true";
        }
    }

    start() {
        this.computeMaxHeight();
        this.updateContent();
        const carouselBS = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
        this.registerCleanup(() => carouselBS.dispose());
    }

    computeMaxHeight() {
        this.maxHeight = undefined;
        for (const itemEl of this.el.querySelectorAll(".carousel-item")) {
            const isActive = itemEl.classList.contains("active");
            itemEl.classList.add("active");
            const height = itemEl.getBoundingClientRect().height;
            if (height > this.maxHeight || this.maxHeight === undefined) {
                this.maxHeight = height;
            }
            itemEl.classList.toggle("active", isActive);
        }
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_slider", CarouselSlider);
