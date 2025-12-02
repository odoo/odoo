declare module "registries" {
    import { Component } from "@odoo/owl";
    import { Provider } from "@web/core/commands/command_palette";

    export interface CommandCategoriesRegistryItemShape {
        name?: string;
        namespace?: string;
    }

    export type CommandProviderRegistryItemShape = Provider;

    export interface CommandSetupRegistryItemShape {
        debounceDelay?: number,
        emptyMessage: string,
        name: string;
        placeholder: string,
    }

    interface GlobalRegistryCategories {
        command_categories: CommandCategoriesRegistryItemShape;
        command_provider: CommandProviderRegistryItemShape;
        command_setup: CommandSetupRegistryItemShape;
    }
}
