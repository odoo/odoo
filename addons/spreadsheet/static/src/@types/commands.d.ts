import {
  CorePlugin,
  UIPlugin,
  DispatchResult,
  CommandResult,
  AddPivotCommand,
  UpdatePivotCommand,
} from "@odoo/o-spreadsheet";
import * as CancelledReason from "@spreadsheet/o_spreadsheet/cancelled_reason";

type CoreDispatch = CorePlugin["dispatch"];
type UIDispatch = UIPlugin["dispatch"];
type CoreCommand = Parameters<CorePlugin["allowDispatch"]>[0];
type Command = Parameters<UIPlugin["allowDispatch"]>[0];

declare module "@spreadsheet" {
  interface OdooCommandDispatcher {
    dispatch<
      T extends OdooCommandTypes,
      C extends Extract<OdooCommand, { type: T }>
    >(
      type: {} extends Omit<C, "type"> ? T : never
    ): DispatchResult;
    dispatch<
      T extends OdooCommandTypes,
      C extends Extract<OdooCommand, { type: T }>
    >(
      type: T,
      r: Omit<C, "type">
    ): DispatchResult;
  }

  interface OdooCoreCommandDispatcher {
    dispatch<
      T extends OdooCoreCommandTypes,
      C extends Extract<OdooCoreCommand, { type: T }>
    >(
      type: {} extends Omit<C, "type"> ? T : never
    ): DispatchResult;
    dispatch<
      T extends OdooCoreCommandTypes,
      C extends Extract<OdooCoreCommand, { type: T }>
    >(
      type: T,
      r: Omit<C, "type">
    ): DispatchResult;
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

  // UI

  export interface RefreshAllDataSourcesCommand {
    type: "REFRESH_ALL_DATA_SOURCES";
  }

  type OdooCoreCommand =
    | ExtendedAddPivotCommand
    | ExtendedUpdatePivotCommand
    | UpdatePivotDomainCommand
    | AddThreadCommand
    | DeleteThreadCommand
    | EditThreadCommand;

  export type AllCoreCommand = OdooCoreCommand | CoreCommand;

  type OdooLocalCommand = RefreshAllDataSourcesCommand;
  type OdooCommand = OdooCoreCommand | OdooLocalCommand;

  export type AllCommand = OdooCommand | Command;
}
