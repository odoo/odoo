import { registry } from "@web/core/registry";
import { Marquee } from "@website/interactions/marquee";

export class ReferencesCarousel extends Marquee {
    static selector = ".s_references_carousel";
    static classPrefix = "s_references_carousel";

    dynamicContent = {
        ...this.dynamicContent,
        // A cell takes the width of its logo, only known once it is loaded.
        // Not for the clones: a layout loads them, so it would loop.
        ".s_references_carousel_marquee_item:not(.o_marquee_item_clone) img": {
            "t-on-load": this.debounced(this.onResize, 100),
        },
    };
}

registry.category("public.interactions").add("website.references_carousel", ReferencesCarousel);
