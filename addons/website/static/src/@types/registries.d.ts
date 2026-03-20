declare module "registries" {
    import { Plugin } from "@html_editor/plugin";
    import { Interaction } from "@web/public/interaction";

    type Constructor<T = {}> = new (arg: T) => T;
    export type EditInteractionMixin = Constructor<Interaction>;
    export type PreviewInteractionMixin = Constructor<Interaction>;

    export interface EditInteractionRegistryItemShape {
        Interaction: Interaction;
        mixin?: EditInteractionMixin;
    }
    export interface PreviewInteractionRegistryItemShape {
        Interaction: Interaction;
        mixin?: PreviewInteractionMixin;
    }

    export type WebsitePluginRegistryItemShape = typeof Plugin;
    export type TranslationPluginRegistryItemShape = typeof Plugin;

    export interface GlobalRegistryCategories {
        "public.interactions.edit": EditInteractionRegistryItemShape;
        "public.interactions.preview": PreviewInteractionRegistryItemShape;
        "translation-plugins": TranslationPluginRegistryItemShape;
        "website-plugins": WebsitePluginRegistryItemShape;
    }
}
