declare module "plugins" {
    import { suggestion_sources } from "@mail/core/common/plugin/suggestion/suggestion_plugin";

    export interface EditorResourcesList {
        suggestion_sources: suggestion_sources;
    }
}
