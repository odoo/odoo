import { FieldMatching } from "./global_filter.d";
import {
    CorePlugin,
    UIPlugin,
    DispatchResult,
    CommandResult,
    AddPivotCommand,
    UpdatePivotCommand,
    CancelledReason,
} from "@odoo/o-spreadsheet";
import * as OdooCancelledReason from "@spreadsheet/o_spreadsheet/cancelled_reason";

type CoreDispatch = CorePlugin["dispatch"];
type UIDispatch = UIPlugin["dispatch"];
type CoreCommand = Parameters<CorePlugin["allowDispatch"]>[0];
type Command = Parameters<UIPlugin["allowDispatch"]>[0];

// TODO look for a way to remove this and use the real import * as OdooCancelledReason
type OdooCancelledReason = string;

declare module "@spreadsheet" {
    interface OdooCommandDispatcher {
        dispatch<T extends OdooCommandTypes, C extends Extract<OdooCommand, { type: T }>>(
            type: {} extends Omit<C, "type"> ? T : never
        ): OdooDispatchResult;
        dispatch<T extends OdooCommandTypes, C extends Extract<OdooCommand, { type: T }>>(
            type: T,
            r: Omit<C, "type">
        ): OdooDispatchResult;
    }

    interface OdooCoreCommandDispatcher {
        dispatch<T extends OdooCoreCommandTypes, C extends Extract<OdooCoreCommand, { type: T }>>(
            type: {} extends Omit<C, "type"> ? T : never
        ): OdooDispatchResult;
        dispatch<T extends OdooCoreCommandTypes, C extends Extract<OdooCoreCommand, { type: T }>>(
            type: T,
            r: Omit<C, "type">
        ): OdooDispatchResult;
    }

    interface OdooDispatchResult extends DispatchResult {
        readonly reasons: (CancelledReason | OdooCancelledReason)[];
        isCancelledBecause(reason: CancelledReason | OdooCancelledReason): boolean;
    }

    type OdooCommandTypes = OdooCommand["type"];
    type OdooCoreCommandTypes = OdooCoreCommand["type"];

    type OdooDispatch = UIDispatch & OdooCommandDispatcher["dispatch"];
    type OdooCoreDispatch = CoreDispatch & OdooCoreCommandDispatcher["dispatch"];

    // CORE

    export interface ExtendedAddPivotCommand extends AddPivotCommand {
        pivot: ExtendedPivotCoreDefinition;
    }

    export interface ExtendedUpdatePivotCommand extends UpdatePivotCommand {
        pivot: ExtendedPivotCoreDefinition;
    }

    export interface AddThreadCommand {
        type: "ADD_COMMENT_THREAD";
        threadId: number;
        sheetId: string;
        col: number;
        row: number;
    }

    export interface EditThreadCommand {
        type: "EDIT_COMMENT_THREAD";
        threadId: number;
        sheetId: string;
        col: number;
        row: number;
        isResolved: boolean;
    }

    export interface DeleteThreadCommand {
        type: "DELETE_COMMENT_THREAD";
        threadId: number;
        sheetId: string;
        col: number;
        row: number;
    }

    // this command is deprecated. use UPDATE_PIVOT instead
    export interface UpdatePivotDomainCommand {
        type: "UPDATE_ODOO_PIVOT_DOMAIN";
        pivotId: string;
        domain: Array;
    }

    export interface AddGlobalFilterCommand {
        type: "ADD_GLOBAL_FILTER";
        filter: CmdGlobalFilter;
        [string]: any; // Fields matching
    }

    export interface EditGlobalFilterCommand {
        type: "EDIT_GLOBAL_FILTER";
        filter: CmdGlobalFilter;
        [string]: any; // Fields matching
    }

    export interface RemoveGlobalFilterCommand {
        type: "REMOVE_GLOBAL_FILTER";
        id: string;
    }

    export interface MoveGlobalFilterCommand {
        type: "MOVE_GLOBAL_FILTER";
        id: string;
        delta: number;
    }

    // UI

    export interface RefreshAllDataSourcesCommand {
        type: "REFRESH_ALL_DATA_SOURCES";
    }

    export interface SetGlobalFilterValueCommand {
        type: "SET_GLOBAL_FILTER_VALUE";
        id: string;
        value: any;
    }

    export interface SetManyGlobalFilterValueCommand {
        type: "SET_MANY_GLOBAL_FILTER_VALUE";
        filters: { filterId: string; value: any }[];
    }

    type OdooCoreCommand =
        | ExtendedAddPivotCommand
        | ExtendedUpdatePivotCommand
        | UpdatePivotDomainCommand
        | AddThreadCommand
        | DeleteThreadCommand
        | EditThreadCommand
        | AddGlobalFilterCommand
        | EditGlobalFilterCommand
        | RemoveGlobalFilterCommand
        | MoveGlobalFilterCommand;

    export type AllCoreCommand = OdooCoreCommand | CoreCommand;

    type OdooLocalCommand =
        | RefreshAllDataSourcesCommand
        | SetGlobalFilterValueCommand
        | SetManyGlobalFilterValueCommand;

    type OdooCommand = OdooCoreCommand | OdooLocalCommand;

    export type AllCommand = OdooCommand | Command;
}
