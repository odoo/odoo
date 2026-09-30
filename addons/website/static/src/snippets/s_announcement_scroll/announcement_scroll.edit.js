import { registry } from "@web/core/registry";
import { AnnouncementScroll } from "./announcement_scroll";

export const AnnouncementScrollEdit = (I) =>
    class extends I {
        shouldStop() {
            // Should always restart, because each option may modify the width of
            // the element, meaning the interaction needs to recompute.
            return true;
        }
        isImpactedBy(el) {
            // After an update of the font family or the text content.
            return (
                this.el.contains(el) &&
                el.matches(
                    `.s_announcement_scroll_marquee_container,
                    .s_announcement_scroll_marquee_item:first-child,
                    .s_announcement_scroll_marquee_item:first-child > [data-oe-translation-source-sha]`
                )
            );
        }
    };

registry.category("public.interactions.edit").add("website.announcement_scroll", {
    Interaction: AnnouncementScroll,
    mixin: AnnouncementScrollEdit,
});
