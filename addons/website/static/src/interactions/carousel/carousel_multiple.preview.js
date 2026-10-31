import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class CarouselMultiplePreview extends Interaction {
    static selector = ".s_carousel_multiple";

    dynamicContent = {
        _root: {
            // The slide is triggered by the CarouselSliderPreview interaction.
            "t-on-slide.bs.carousel": this.onSlideCarousel,
            "t-on-slid.bs.carousel": this.onSlidCarousel,
        },
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.carouselItemEls = this.el.querySelectorAll(".carousel-item");
    }

    destroy() {
        this.el.style.removeProperty("--carousel-multiple-current-index");
    }

    onSlideCarousel(ev) {
        // Make the items slide.
        this.el.style.setProperty("--carousel-multiple-current-index", ev.to);
    }

    onSlidCarousel(ev) {
        // Go back to the first slide if we reached the last valid indicator.
        const nbDisplayedItems = parseInt(
            getComputedStyle(this.el).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        if (ev.to >= this.carouselItemEls.length - nbDisplayedItems) {
            this.bootstrap.getOrCreateInstance(window.Carousel, this.el).to(0);
        }
    }
}

registry
    .category("public.interactions.preview")
    .add("website.carousel_multiple_preview", { Interaction: CarouselMultiplePreview });
