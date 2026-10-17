import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        region_properties: { is: "div.carousel-item", overlayButtons: false },
        anchor_excluded_selectors: ".carousel *",
    };
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
