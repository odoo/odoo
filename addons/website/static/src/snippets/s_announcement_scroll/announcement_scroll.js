import { registry } from "@web/core/registry";
import { Marquee } from "@website/interactions/marquee";

export class AnnouncementScroll extends Marquee {
    static selector = ".s_announcement_scroll";
    static classPrefix = "s_announcement_scroll";

    /**
     * @override
     */
    prepareClone(cloneEl) {
        super.prepareClone(cloneEl);
        // Separate consecutive text strips with a non-breaking space.
        cloneEl.prepend(document.createTextNode("\u00A0"));
    }
}

registry.category("public.interactions").add("website.announcement_scroll", AnnouncementScroll);
