import { registry } from "@web/core/registry";
import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { EventsMixin } from "./events_mixin";

const EventsCarouselBase = EventsMixin(DynamicSnippetCarousel);

export class EventsCarousel extends EventsCarouselBase {
    static selector = ".s_events_carousel";
}

registry.category("public.interactions.edit").add("website_event.events_carousel_base", {
    Interaction: EventsCarouselBase,
    isAbstract: true,
});

registry.category("public.interactions").add("website_event.events_carousel", EventsCarousel);

registry.category("public.interactions.edit").add("website_event.events_carousel", {
    Interaction: EventsCarousel,
});
