declare module "@spreadsheet" {
    import { CommandResult, CorePlugin, UIPlugin } from "@odoo/o-spreadsheet";
    import { CommandResult as CR } from "@spreadsheet/o_spreadsheet/cancelled_reason";
    type OdooCommandResult = CommandResult | typeof CR;

    /**
     * Keys are either a command type or a command set name (prefixed with `*`).
     */
    type OdooCommandHandlers<Cmd> = Record<string, (command: Cmd) => void>;
    type OdooCommandValidators<Cmd> = Record<string, (command: Cmd) => string | string[]>;

    export interface OdooCorePlugin extends CorePlugin {
        getters: OdooCoreGetters;
        dispatch: OdooCoreDispatch;
        validators: OdooCommandValidators<AllCoreCommand>;
        preHandlers: OdooCommandHandlers<AllCoreCommand>;
        handlers: OdooCommandHandlers<AllCoreCommand>;
    }

    export interface OdooCorePluginConstructor {
        new (config: unknown): OdooCorePlugin;
    }

    export interface OdooUIPlugin extends UIPlugin {
        getters: OdooGetters;
        dispatch: OdooDispatch;
        validators: OdooCommandValidators<AllCommand>;
        preHandlers: OdooCommandHandlers<AllCommand>;
        handlers: OdooCommandHandlers<AllCommand>;
    }

    export interface OdooUIPluginConstructor {
        new (config: unknown): OdooUIPlugin;
    }
}
