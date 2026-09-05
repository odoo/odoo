import { registry } from "@web/core/registry";
import { ReferencesCarousel } from "./references_carousel";

/**
 * Unlike `s_announcement_scroll`, nothing is derived from the strip width in
 * edit mode: the layout is fully handled by the edit stylesheet. Hence no
 * `shouldStop` / `isImpactedBy` override, the interaction has no state to
 * refresh when an option or a logo changes.
 */
export const ReferencesCarouselEdit = (I) =>
    class extends I {
        start() {
            // Neither clones nor animation: `marqueeReady` stays false, so the
            // single strip of logos is simply laid out as a wrapping grid where
            // each logo stays visible and easy to select.
            this.undoMarqueeLayout();
            this.marqueeReady = false;
            this.updateContent();
        }

        onResize() {
            // Nothing to recompute, the wrapping grid reflows on its own.
        }

        updateMarqueeLayout() {
            // No clone in edit mode.
        }
    };

registry.category("public.interactions.edit").add("website.references_carousel", {
    Interaction: ReferencesCarousel,
    mixin: ReferencesCarouselEdit,
});
