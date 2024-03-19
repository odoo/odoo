import { OdooPivotRuntimeDefinition } from "@spreadsheet/pivot/pivot_runtime";
import { ORM } from "@web/core/orm_service";
import { PivotMeasure } from "@spreadsheet/pivot/pivot_runtime";
import { SpreadsheetPivotTable } from "@spreadsheet/pivot/pivot_table";
import { ServerData } from "@spreadsheet/data_sources/server_data";

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
        getPivotMeasureFormat(name: string): string | undefined;
        assertIsValid({ throwOnError }: { throwOnError: boolean }): boolean;
    }

    export type Aggregator = "array_agg" | "count" | "count_distinct" | "bool_and" | "bool_or" | "max" | "min" | "avg" | "sum";
    export type Granularity = "day" | "week" | "month" | "quarter" | "year";

    export interface PivotDimensionDefinition {
        name: string;
        order?: "asc" | "desc";
        granularity?: Granularity | string;
    }

    export interface PivotMeasureDefinition {
        name: string;
        aggregator?: Aggregator | string;
    }

    export interface PivotMeasure extends PivotMeasureDefinition {
        nameWithAggregator: string;
        displayName: string | LazyTranslatedString;
        type: string;
    }

    export interface PivotDimension extends PivotDimensionDefinition {
        nameWithGranularity: string;
        displayName: string | LazyTranslatedString;
        type: string;
    }

    export interface CommonPivotDefinition {
      columns: PivotDimensionDefinition[];
      rows: PivotDimensionDefinition[];
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
        aggregator?: string;
        store?: boolean;
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
        serverData: ServerData
        orm: ORM;
    }
}
