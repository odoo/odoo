import { MetadataRepository } from "@spreadsheet/data_sources/metadata_repository";
import { OdooPivotRuntimeDefinition } from "@spreadsheet/pivot/pivot_runtime";
import { ORM } from "@web/core/orm_service";
import { PivotMeasure } from "@spreadsheet/pivot/pivot_runtime";
import { SpreadsheetPivotTable } from "@spreadsheet/pivot/pivot_table";

declare module "@spreadsheet" {
    interface SortedColumn {
        groupId: number;
        measure: string;
        order: string;
    }


    export interface Pivot<T> {
        definition: T;
        getMeasure: (name: string) => PivotMeasure;
        computePivotHeaderValue(domain: Array<string | number>): string | boolean | number;
        getLastPivotGroupValue(domain: Array<string | number>): string | boolean | number;
        getTableStructure(): SpreadsheetPivotTable;
        getPivotCellValue(measure: string, domain: Array<string | number>): string | boolean | number;
        getPivotFieldFormat(name: string): string;
    }

    export interface CommonPivotDefinition {
      colGroupBys: string[];
      rowGroupBys: string[];
      measures: string[];
      name: string;
      sortedColumn: SortedColumn | null;
    }

    export interface OdooPivotDefinition extends CommonPivotDefinition {
        type: "ODOO";
        model: string;
        domain: Array;
        context: Object;
        actionXmlId: string;
    }

    export interface SpreadsheetPivotDefinition extends CommonPivotDefinition {
        type: "SPREADSHEET";
        range: string;
    }

    export interface GFLocalPivot {
      id: string;
      fieldMatching: Record<string, any>;
    }

    export type PivotDefinition = OdooPivotDefinition | SpreadsheetPivotDefinition;

    export type CorePivotDefinition = PivotDefinition & {
        formulaId: string;
    }

    export interface Field {
        name: string;
        type: string;
        string: string;
        relation?: string;
        searchable?: boolean;
    }

    export type Fields = Record<string, Field | undefined>;

    export interface PivotMetaData {
        colGroupBys: string[];
        rowGroupBys: string[];
        activeMeasures: string[];
        resModel: string;
        fields?: Record<string, Field | undefined>;
        modelLabel?: string;
        sortedColumn: SortedColumn | null;
        fieldAttrs: any;
    }

    export interface PivotSearchParams {
        groupBy: string[];
        orderBy: string[];
        domain: Array;
        context: Object;
    }

    // Spreadsheet Table
    export interface SPTableColumn {
        fields: string[];
        values: string[];
        width: number;
        offset: number;
    }

    export interface SPTableRow {
        fields: string[];
        values: string[];
        indent: number;
    }

    export interface SPTableData {
        cols: SPTableColumn[][];
        rows: SPTableRow[];
        measures: string[];
        rowTitle: string;
    }

    export interface SPTableCell {
        isHeader: boolean;
        domain?: string[];
        content?: string;
        style?: object;
        measure?: string;
    }

    /* Params used for the odoo pivot model */
    export interface WebPivotModelParams {
        metaData: PivotMetaData;
        searchParams: PivotSearchParams;
    }

    export interface OdooPivotModelParams {
        metaData: {
            resModel: string;
            fields: Record<string, Field | undefined>;
        };
        definition: OdooPivotRuntimeDefinition;
        searchParams: {
            domain: Array;
            context: Object;
        };
    }

    export interface PivotModelServices {
        metadataRepository: MetadataRepository;
        orm: ORM;
    }
}
