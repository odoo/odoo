declare module "@spreadsheet" {
    import { CommandResult, CorePlugin, UIPlugin } from "@odoo/o-spreadsheet";
    import { CommandResult as CR } from "@spreadsheet/o_spreadsheet/cancelled_reason";
    type OdooCommandResult = CommandResult | typeof CR;

    export interface OdooCorePlugin extends CorePlugin {
        getters: OdooCoreGetters;
        dispatch: OdooCoreDispatch;
        allowDispatch(command: AllCoreCommand): string | string[];
        beforeHandle(command: AllCoreCommand): void;
        handle(command: AllCoreCommand): void;
    }

    export interface OdooCorePluginConstructor {
        new (config: unknown): OdooCorePlugin;
    }

    export interface OdooUIPlugin extends UIPlugin {
        getters: OdooGetters;
        dispatch: OdooDispatch;
        allowDispatch(command: AllCommand): string | string[];
        beforeHandle(command: AllCommand): void;
        handle(command: AllCommand): void;
    }

    export interface OdooUIPluginConstructor {
        new (config: unknown): OdooUIPlugin;
    }
}
