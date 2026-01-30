import { registry } from "@web/core/registry";
import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { EventsMixin } from "./events_mixin";

export class DynamicSnippetCarouselEvents extends EventsMixin(DynamicSnippetCarousel) {
    static selector = ".s_events_carousel";

    renderContent() {
        super.renderContent();
        const rowEl = this.el.querySelectorAll(".s_dynamic_snippet_row");
        rowEl.forEach((row) => {
            row.classList.remove("s_dynamic_snippet_row");
        });
    }
}

registry
    .category("public.interactions")
    .add("website_event.event_carousel", DynamicSnippetCarouselEvents);

registry.category("public.interactions.edit").add("website_event.event_carousel", {
    Interaction: DynamicSnippetCarouselEvents,
});
