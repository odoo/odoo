import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSearchInfoAction } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { DynamicSearchInfoTagIdsByCategoryAction },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_event_upcoming_snippet, .s_events_carousel")) {
                return "event.event";
            }
        },
    };
}

export class DynamicSearchInfoTagIdsByCategoryAction extends DynamicSearchInfoAction {
    static id = "dynamicSearchInfoTagIdsByCategory";
    getValue(args) {
        const searchInfoValue = super.getValue(args);
        if (searchInfoValue) {
            const searchInfo = Object.entries(searchInfoValue).flatMap(([category_id, ids]) =>
                ids.map((id) => ({ id, category_id: [category_id] }))
            );
            return JSON.stringify(searchInfo);
        }
    }
    apply(args) {
        const value = {};
        for (const { category_id, id } of JSON.parse(args.value)) {
            value[category_id[0]] ||= [];
            value[category_id[0]].push(id);
        }
        Object.keys(value).length ? super.apply({ ...args, value }) : super.clean(args);
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
