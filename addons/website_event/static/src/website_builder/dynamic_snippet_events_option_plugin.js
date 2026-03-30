import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dynamic_filter_search_domain_processors: (domain, { eventByTagIds }) => {
            if (eventByTagIds) {
                const tagsByCategory = Map.groupBy(eventByTagIds, (tag) => tag.category_id[0]);
                for (const tags of tagsByCategory.values()) {
                    domain.push(["tag_ids", "in", tags.map((e) => e.id)]);
                }
            }
            return domain;
        },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_event_upcoming_snippet")) {
                return "event.event";
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
