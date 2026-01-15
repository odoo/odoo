import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";

const DynamicSnippetCarouselEdit = (I) =>
    class extends I {
        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            if (this.el.classList.contains("o_carousel_multi_items")) {
                snapshot = JSON.parse(snapshot || "{}");
                snapshot.multi_items = true;
                snapshot = JSON.stringify(snapshot);
            }
            return snapshot;
        }
    };

registry.category("public.interactions.edit").add("website.dynamic_snippet_carousel", {
    Interaction: DynamicSnippetCarousel,
    mixin: DynamicSnippetCarouselEdit,
});
