declare module "registries" {
    import { Plugin } from "@html_editor/plugin";
    import { BaseOptionComponent } from "@html_builder/core/base_option_component";

    export type BuilderPluginRegistryItemShape = typeof Plugin;
    export type BuilderOptionRegistryItemShape = typeof BaseOptionComponent;

    export interface GlobalRegistryCategories {
        "builder-options": BuilderOptionRegistryItemShape;
        "builder-plugins": BuilderPluginRegistryItemShape;
    }
}
