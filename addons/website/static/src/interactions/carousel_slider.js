import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

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
                "min-height": this.maxHeight,
            }),
        },
    };
    carouselOptions = undefined;

    setup() {
        this.maxHeight = undefined;
    }

    start() {
        this.computeMaxHeight();
        const carouselBS = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
        this.registerCleanup(() => carouselBS.dispose());
    }

    computeMaxHeight() {
        this.maxHeight = undefined;
        for (const itemEl of this.el.querySelectorAll(".carousel-item")) {
            const isActive = itemEl.classList.contains("active");
            itemEl.classList.add("active");
            const rect = itemEl.getBoundingClientRect();
            const height = rect.height;
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
