import {
  CorePlugin,
  UIPlugin,
  DispatchResult,
  CommandResult,
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

  export interface InsertPivotCommand {
    type: "INSERT_PIVOT";
    id: string;
    sheetId: string;
    col: number;
    row: number;
    table: SPTableData;
    definition: PivotRuntime;
  }

  export interface ReInsertPivotCommand {
    type: "RE_INSERT_PIVOT";
    id: string;
    sheetId: string;
    col: number;
    row: number;
    table: SPTableData;
  }

  export interface RenamePivotCommand {
    type: "RENAME_ODOO_PIVOT";
    pivotId: string;
    name: string;
  }

  export interface RemovePivotCommand {
    type: "REMOVE_PIVOT";
    pivotId: string;
  }

  export interface DuplicatePivotCommand {
    type: "DUPLICATE_PIVOT";
    pivotId: string;
    newPivotId: string;
  }

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
    | InsertPivotCommand
    | ReInsertPivotCommand
    | RenamePivotCommand
    | RemovePivotCommand
    | DuplicatePivotCommand
    | UpdatePivotDomainCommand;
  export type AllCoreCommand = OdooCoreCommand | CoreCommand;

  type OdooLocalCommand = RefreshAllDataSourcesCommand;
  type OdooCommand = OdooCoreCommand | OdooLocalCommand;

  export type AllCommand = OdooCommand | Command;
}
