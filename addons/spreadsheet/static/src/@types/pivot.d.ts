declare module "@spreadsheet" {
    interface SortedColumn {
        groupId: number;
        measure: string;
        order: string;
    }

    export interface PivotDefinition {
        colGroupBys: string[];
        rowGroupBys: string[];
        measures: string[];
        model: string;
        domain: Array;
        context: Object;
        name: string;
        sortedColumn: SortedColumn | null;
    }

    export interface Field {
        name: string;
        type: string;
        string: string;
        relation?: string;
        searchable?: boolean;
    }

    export interface PivotMetaData {
        colGroupBys: string[];
        rowGroupBys: string[];
        activeMeasures: string[];
        resModel: string;
        fields?: Record<string, Field | undefined>;
        modelLabel?: string;
        sortedColumn: SortedColumn | null;
    }

    export interface PivotSearchParams {
        groupBy: string[];
        orderBy: string[];
        domain: Array;
        context: Object;
    }

    // Spreadsheet Table
    interface SPTableColumn {
        fields: string[];
        values: string[];
        width: number;
        offset: number;
    }

    interface SPTableRow {
        fields: string[];
        values: string[];
        intend: number;
    }

    interface SPTableData {
        cols: SPTableColumn[][];
        rows: SPTableRow[];
        measures: string[];
        rowTitle: string;
    }

    /* Params used for the odoo pivot model */
    export interface PivotRuntime {
        metaData: PivotMetaData;
        searchParams: PivotSearchParams;
        name: string;
    }
}
