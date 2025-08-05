import * as spreadsheet from "@odoo/o-spreadsheet";
const { inverseCommandRegistry, otRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

otRegistry.addTransformation(
    "DELETE_CHART",
    ["UPDATE_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        if (executed.chartId === toTransform.chartId) {
            return undefined;
        }
        const { dataSourceCoreId, type } = toTransform.odooDataSource;
        if (type === "chart" && executed.figureId === dataSourceCoreId) {
            return undefined;
        }
        return toTransform;
    }
);

otRegistry.addTransformation(
    "REMOVE_PIVOT",
    ["UPDATE_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        const { dataSourceCoreId, type } = toTransform.odooDataSource;
        if (type === "pivot" && dataSourceCoreId === executed.pivotId) {
            return undefined;
        }
        return toTransform;
    }
);

otRegistry.addTransformation(
    "REMOVE_ODOO_LIST",
    ["UPDATE_ODOO_LINK_TO_CHART"],
    (toTransform, executed) => {
        const { dataSourceCoreId, type } = toTransform.odooDataSource;
        if (type === "list" && dataSourceCoreId === executed.listId) {
            return undefined;
        }
        return toTransform;
    }
);

inverseCommandRegistry.add("UPDATE_ODOO_LINK_TO_CHART", identity);
