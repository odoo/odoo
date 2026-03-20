import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class DynamicSnippetEventsOption extends BaseOptionComponent {
    static template = "website_event.DynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetEventsOption"];
    static selector = ".s_event_upcoming_snippet";
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
