import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        properties: { predicate: "div.carousel-item", overlayButtons: false },
        anchor_excluded_selectors: ".carousel *",
        can_have_block_hover_effect_predicates: this.canHaveHoverEffect.bind(this),
        can_have_image_hover_effect_predicates: this.canHaveHoverEffect.bind(this),
    };
    canHaveHoverEffect(el) {
        if (el.closest("*:has(> .slide-link)")) {
            return false;
        }
    }
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
