import { registry } from "@web/core/registry";
import { Marquee } from "@website/interactions/marquee";

export class ReferencesCarousel extends Marquee {
    static selector = ".s_references_carousel";
    static classPrefix = "s_references_carousel";
}

registry.category("public.interactions").add("website.references_carousel", ReferencesCarousel);
