import { registry } from "@web/core/registry";
import { Marquee } from "@website/interactions/marquee";

export class ReferencesCarousel extends Marquee {
    static selector = ".s_references_carousel";
    static classPrefix = "s_references_carousel";

    dynamicContent = {
        ...this.dynamicContent,
        // Each cell takes the width of its logo: lay the strip out again once
        // a logo is loaded, as its width only then becomes known. Only the
        // original logos: a clone loading is caused by a layout, and laying
        // the strip out again would clone it again, endlessly.
        ".s_references_carousel_marquee_item:not(.s_references_carousel_marquee_item_clone) img": {
            "t-on-load": this.debounced(this.onResize, 100),
        },
    };
}

registry.category("public.interactions").add("website.references_carousel", ReferencesCarousel);
