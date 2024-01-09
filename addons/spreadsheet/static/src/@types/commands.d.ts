import { CorePlugin, UIPlugin, DispatchResult, CommandResult } from "@odoo/o-spreadsheet";
import * as CancelledReason from "@spreadsheet/o_spreadsheet/cancelled_reason";

type CoreDispatch = CorePlugin["dispatch"];
type UIDispatch = UIPlugin["dispatch"];
type CoreCommand = Parameters<CorePlugin["allowDispatch"]>[0];
type Command = Parameters<UIPlugin["allowDispatch"]>[0];

declare module "@spreadsheet" {
    interface OdooCommandDispatcher {
        dispatch<T extends OdooCommandTypes, C extends Extract<OdooCommand, { type: T }>>(
            type: {} extends Omit<C, "type"> ? T : never
        ): DispatchResult;
        dispatch<T extends OdooCommandTypes, C extends Extract<OdooCommand, { type: T }>>(
            type: T,
            r: Omit<C, "type">
        ): DispatchResult;
    }

    interface OdooCoreCommandDispatcher {
        dispatch<T extends OdooCoreCommandTypes, C extends Extract<OdooCoreCommand, { type: T }>>(
            type: {} extends Omit<C, "type"> ? T : never
        ): DispatchResult;
        dispatch<T extends OdooCoreCommandTypes, C extends Extract<OdooCoreCommand, { type: T }>>(
            type: T,
            r: Omit<C, "type">
        ): DispatchResult;
    }

    type OdooCommandTypes = OdooCommand["type"];
    type OdooCoreCommandTypes = OdooCoreCommand["type"];

    type OdooDispatch = UIDispatch & OdooCommandDispatcher["dispatch"];
    type OdooCoreDispatch = CoreDispatch & OdooCoreCommandDispatcher["dispatch"];

    // CORE

    export interface INSERT_PIVOT_COMMAND {
        type: "INSERT_PIVOT";
        id: string;
        sheetId: string;
        col: number;
        row: number;
        table: SPTableData;
        definition: PivotRuntime;
    }

    export interface RE_INSERT_PIVOT_COMMAND {
        type: "RE_INSERT_PIVOT";
        id: string;
        sheetId: string;
        col: number;
        row: number;
        table: SPTableData;
    }

    export interface RENAME_PIVOT_COMMAND {
        type: "RENAME_ODOO_PIVOT";
        pivotId: string;
        name: string;
    }

    export interface REMOVE_PIVOT_COMMAND {
        type: "REMOVE_PIVOT";
        pivotId: string;
    }

    export interface DUPLICATE_PIVOT_COMMAND {
        type: "DUPLICATE_PIVOT";
        pivotId: string;
        newPivotId: string;
    }

    export interface UPDATE_PIVOT_DOMAIN_COMMAND {
        type: "UPDATE_ODOO_PIVOT_DOMAIN";
        pivotId: string;
        domain: Array;
    }

    // UI

    export interface REFRESH_ALL_DATA_SOURCES_COMMAND {
        type: "REFRESH_ALL_DATA_SOURCES";
    }

    type OdooCoreCommand =
        | INSERT_PIVOT_COMMAND
        | RE_INSERT_PIVOT_COMMAND
        | RENAME_PIVOT_COMMAND
        | REMOVE_PIVOT_COMMAND
        | DUPLICATE_PIVOT_COMMAND
        | UPDATE_PIVOT_DOMAIN_COMMAND;
    export type AllCoreCommand = OdooCoreCommand | CoreCommand;

    type OdooLocalCommand = REFRESH_ALL_DATA_SOURCES_COMMAND;
    type OdooCommand = OdooCoreCommand | OdooLocalCommand;

    export type AllCommand = OdooCommand | Command;
}
