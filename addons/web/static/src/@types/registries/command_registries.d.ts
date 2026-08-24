declare module "registries" {
    import { Component } from "@odoo/owl";
    import { Provider } from "@web/core/commands/command_palette";

    export interface CommandCategoriesRegistryItemShape {
        name?: TranslatedString;
        namespace?: string;
    }

    export type CommandProviderRegistryItemShape = Provider;

    export interface CommandSetupRegistryItemShape {
        debounceDelay?: number,
        emptyMessage: TranslatedString,
        name: TranslatedString;
        placeholder: TranslatedString,
    }

    interface GlobalRegistryCategories {
        command_categories: CommandCategoriesRegistryItemShape;
        command_provider: CommandProviderRegistryItemShape;
        command_setup: CommandSetupRegistryItemShape;
    }
}
