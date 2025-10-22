declare module "registries" {
    import { Plugin } from "@html_editor/plugin";

    export type BuilderPluginRegistryItemShape = typeof Plugin;

    export interface GlobalRegistryCategories {
        "builder-plugins": BuilderPluginRegistryItemShape;
    }
}
