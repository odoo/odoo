import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { EventsMixin } from "./events_mixin";

export class Events extends EventsMixin(DynamicSnippet) {
    // While the selector has 'upcoming_snippet' in its name, it now has a filter
    // option to include ongoing events. The name is kept for backward compatibility.
    static selector = ".s_event_upcoming_snippet";
}

registry
    .category("public.interactions")
    .add("website_event.events", Events);

registry
    .category("public.interactions.edit")
    .add("website_event.events", {
        Interaction: Events,
    });
