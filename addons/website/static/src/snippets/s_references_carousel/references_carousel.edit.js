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
            // single strip of logos stays still, in a row that scrolls
            // horizontally where each logo stays easy to select.
        }

        onResize() {
            // Nothing to recompute, the row reflows on its own.
        }

        onScroll() {
            // Nothing to drive: the row neither moves (parallax) nor reacts
            // to hover.
        }
    };

registry.category("public.interactions.edit").add("website.references_carousel", {
    Interaction: ReferencesCarousel,
    mixin: ReferencesCarouselEdit,
});
