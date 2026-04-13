import { registry } from "@web/core/registry";
import { ReferencesCarousel } from "./references_carousel";

export const ReferencesCarouselEdit = (I) =>
    class extends I {
        start() {
            // Clean up any cloned groups persisted in saved HTML. The
            // _clone class may have been stripped during save, so remove
            // all groups except the first (original) one.
            const groups = this.containerEl.querySelectorAll(".s_references_carousel_group");
            for (let i = 1; i < groups.length; i++) {
                groups[i].remove();
            }
            this.containerEl.style.removeProperty("--carousel-group-size");
        }
        updateCarouselLayout() {}
        onResize() {}
        shouldStop() {
            return true;
        }
    };

registry.category("public.interactions.edit").add("website.references_carousel", {
    Interaction: ReferencesCarousel,
    mixin: ReferencesCarouselEdit,
});
