import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOption extends BaseOptionComponent {
    static id = "dynamic_snippet_events_option";
    static template = "website_event.DynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetEventsOption"];

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetEventsOption;
        this.modelNameFilter = getModelNameFilter();
        this.dynamicOptionParams = useDynamicSnippetOption(this.modelNameFilter);
        this.templateKeyState = useDomState((el) => ({
            templateKey: el.dataset.templateKey,
        }));
    }
    showCoverImageOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_event.dynamic_filter_template_event_event_single_aside"
        );
    }
}

registry.category("builder-options").add(DynamicSnippetEventsOption.id, DynamicSnippetEventsOption);
