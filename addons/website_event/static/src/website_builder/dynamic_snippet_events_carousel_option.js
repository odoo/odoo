import { registry } from "@web/core/registry";
import { DynamicSnippetEventsOption } from "./dynamic_snippet_events_option";

export class DynamicSnippetEventsCarouselOption extends DynamicSnippetEventsOption {
    static id = "dynamic_snippet_events_carousel_option";
    static template = "website_event.DynamicSnippetEventsCarouselOption";
}

registry
    .category("website-options")
    .add(DynamicSnippetEventsCarouselOption.id, DynamicSnippetEventsCarouselOption);
