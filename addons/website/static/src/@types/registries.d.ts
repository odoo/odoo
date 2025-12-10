
declare module "registries" {
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

    export interface GlobalRegistryCategories {
        "public.interactions.edit": EditInteractionRegistryItemShape;
        "public.interactions.preview": PreviewInteractionRegistryItemShape;
    }
}
