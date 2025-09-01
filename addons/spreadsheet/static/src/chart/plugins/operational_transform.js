import * as spreadsheet from "@odoo/o-spreadsheet";
const { inverseCommandRegistry, otRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

otRegistry.addTransformation(
    "DELETE_CHART",
    ["SET_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        if (executed.chartId === toTransform.chartId) {
            return undefined;
        }
        const { dataSourceId, type } = toTransform.odooDataSource;
        if (type === "chart" && executed.figureId === dataSourceId) {
            return undefined;
        }
        return toTransform;
    }
);

otRegistry.addTransformation(
    "REMOVE_PIVOT",
    ["SET_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        const { dataSourceId, type } = toTransform.odooDataSource;
        if (type === "pivot" && dataSourceId === executed.pivotId) {
            return undefined;
        }
        return toTransform;
    }
);

otRegistry.addTransformation(
    "REMOVE_ODOO_LIST",
    ["SET_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        const { dataSourceId, type } = toTransform.odooDataSource;
        if (type === "list" && dataSourceId === executed.listId) {
            return undefined;
        }
        return toTransform;
    }
);

// add transformation pour les remove pivotFormulaRegex, remove list and delete figure?

inverseCommandRegistry.add("SET_ODOO_LINK_TO_CHART", identity);
