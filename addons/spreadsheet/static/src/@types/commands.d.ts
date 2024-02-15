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

  type AddPivotDefinition = SpreadsheetPivotDefinition;

  export interface OdooAddPivotPayload {
    type: "ODOO";
    definition: OdooPivotDefinition;
  }

  export type ExtendedAddPivotDefinition =
    | AddPivotDefinition
    | OdooPivotDefinition;

  export interface AddPivotCommand {
    type: "ADD_PIVOT";
    pivotId: string;
    pivot: AddPivotDefinition;
  }

  export interface UpdatePivotCommand {
    type: "UPDATE_PIVOT";
    pivotId: string;
    pivot: ExtendedAddPivotDefinition;
  }

  export interface InsertPivotCommand {
    type: "INSERT_PIVOT";
    pivotId: string;
    sheetId: string;
    col: number;
    row: number;
    table: SPTableData;
  }

  export interface ExtendedAddPivotCommand extends AddPivotCommand {
    pivot: ExtendedAddPivotDefinition;
  }

  export interface RenamePivotCommand {
    type: "RENAME_PIVOT";
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
    | InsertPivotCommand
    | RenamePivotCommand
    | RemovePivotCommand
    | DuplicatePivotCommand
    | UpdatePivotDomainCommand
    | UpdatePivotCommand
    | ExtendedAddPivotCommand;
  export type AllCoreCommand = OdooCoreCommand | CoreCommand;

  type OdooLocalCommand = RefreshAllDataSourcesCommand;
  type OdooCommand = OdooCoreCommand | OdooLocalCommand;

  export type AllCommand = OdooCommand | Command;
}
