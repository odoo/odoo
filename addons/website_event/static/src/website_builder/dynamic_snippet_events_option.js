import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { registry } from "@web/core/registry";
import {
    dynamicContentOfDynamicSnippet,
    getSharedSnippetArg,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

export class DynamicSnippetEventsOption extends BaseOptionComponent {
    static id = "dynamic_snippet_events_option";
    static template = "website_event.DynamicSnippetEventsOption";

    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption();
        this.templateKeyState = useDomState((el) => ({
            templateKey: getSharedSnippetArg(
                dynamicContentOfDynamicSnippet(el),
                "content_template"
            ),
        }));
    }
    showCoverImageOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_event.dynamic_filter_template_event_event_single_aside"
        );
    }
}

registry.category("website-options").add(DynamicSnippetEventsOption.id, DynamicSnippetEventsOption);
