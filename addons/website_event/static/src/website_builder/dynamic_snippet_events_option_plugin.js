import { isDarkColorPalette } from "@website/components/dialog/dark_palette_utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSearchInfoAction } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_dynamic_snippet_template_updated_handlers: this.onTemplateUpdated.bind(this),
        builder_actions: { DynamicSearchInfoTagIdsByCategoryAction },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_event_upcoming_snippet, .s_events_carousel")) {
                return "event.event";
            }
        },
    };
    // TODO: do this on normalize
    // Some single-event templates use `o_cc5` for their content background.
    // The snippet dialog replaces it with `o_cc1` for dark palettes. Since the
    // generic template update still relies on the original `o_cc5` metadata,
    // normalize the actual preset after each template change.
    onTemplateUpdated({ el: snippetEl, template }) {
        if (!snippetEl.matches(".s_event_upcoming_snippet")) {
            return;
        }
        const contentEl = snippetEl.querySelector(".s_dynamic_snippet_content");
        const hasColorPreset = template.contentClasses?.split(" ").includes("o_cc5");
        if (!hasColorPreset) {
            // Avoid carrying a preset from a previously selected single layout.
            contentEl.classList.remove("o_cc1", "o_cc5");
        } else if (isDarkColorPalette(snippetEl.ownerDocument)) {
            contentEl.classList.replace("o_cc5", "o_cc1");
        } else {
            contentEl.classList.replace("o_cc1", "o_cc5");
        }
    }
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
