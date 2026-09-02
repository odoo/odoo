import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        should_show_overlay_buttons_of_ancestor_predicates: (el) => {
            if (el.matches("div.carousel-item")) {
                return true;
            }
        },
        anchor_excluded_selectors: ".carousel *",
    };
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
