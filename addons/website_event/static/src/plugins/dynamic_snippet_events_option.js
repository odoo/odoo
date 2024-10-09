import { Plugin } from "@html_editor/plugin";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetOption } from "@html_builder/plugins/dynamic_snippet_option";

class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "DynamicSnippetEventsOption";
    static dependencies = ["DynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetEventsOption,
            props: {
                ...this.dependencies.DynamicSnippetOption.getComponentProps(),
            },
            selector: ".s_event_upcoming_snippet",
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);

export class DynamicSnippetEventsOption extends DynamicSnippetOption {
    static template = "website_event.DynamicSnippetEventsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        ...DynamicSnippetOption.props,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "event.event";
    }
}
