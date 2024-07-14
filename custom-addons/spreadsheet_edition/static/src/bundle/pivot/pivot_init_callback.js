/** @odoo-module **/
import * as spreadsheet from "@odoo/o-spreadsheet";
import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import { Domain } from "@web/core/domain";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

export function insertPivot(pivotData) {
    const definition = {
        metaData: {
            colGroupBys: [...pivotData.metaData.fullColGroupBys],
            rowGroupBys: [...pivotData.metaData.fullRowGroupBys],
            activeMeasures: [...pivotData.metaData.activeMeasures],
            resModel: pivotData.metaData.resModel,
            fields: pivotData.metaData.fields,
            sortedColumn: pivotData.metaData.sortedColumn,
        },
        searchParams: {
            ...pivotData.searchParams,
            domain: new Domain(pivotData.searchParams.domain).toJson(),
            // groups from the search bar are included in `fullRowGroupBys` and `fullColGroupBys`
            // but takes precedence if they are defined
            groupBy: [],
        },
        name: pivotData.name,
    };
    return async (model) => {
        const pivotId = model.getters.getNextPivotId();
        const dataSourceId = model.getters.getPivotDataSourceId(pivotId);
        model.config.custom.dataSources.add(dataSourceId, PivotDataSource, definition);
        await model.config.custom.dataSources.load(dataSourceId);
        const pivotDataSource = model.config.custom.dataSources.get(dataSourceId);
        // Add an empty sheet in the case of an existing spreadsheet.
        if (!this.isEmptySpreadsheet) {
            const sheetId = uuidGenerator.uuidv4();
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", {
                sheetId,
                position: model.getters.getSheetIds().length,
            });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const structure = pivotDataSource.getTableStructure();
        const table = structure.export();
        const sheetId = model.getters.getActiveSheetId();

        const defWithoutFields = JSON.parse(JSON.stringify(definition));
        defWithoutFields.metaData.fields = undefined;
        const result = model.dispatch("INSERT_PIVOT", {
            sheetId,
            col: 0,
            row: 0,
            table,
            id: pivotId,
            definition: defWithoutFields,
        });
        if (!result.isSuccessful) {
            throw new Error(`Couldn't insert pivot in spreadsheet. Reasons : ${result.reasons}`);
        }
        const columns = [];
        for (let col = 0; col <= table.cols[table.cols.length - 1].length; col++) {
            columns.push(col);
        }
        model.dispatch("AUTORESIZE_COLUMNS", { sheetId, cols: columns });
    };
}
