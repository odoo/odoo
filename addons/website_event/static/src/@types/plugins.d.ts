import { DynamicSnippetEventsOptionPlugin } from "../website_builder/dynamic_snippet_events_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        dynamicSnippetEventsOption: SharedOf<typeof DynamicSnippetEventsOptionPlugin>;
    }
}
