import { registries } from "@odoo/o-spreadsheet";

const { chartTypeRegistry } = registries;

// Legacy compatibility: before dataSetStyles was added to the definition, identified with an id,
// styles were stored in an array in the same order as datasets.
// We can't properly upgrade it at upgrade time because we don't have the actual data.
// This code migrates from the old format to the new one.

const hierarchical = ["sunburst", "treemap"];

for (const chartTypeBuilder of chartTypeRegistry.getAll()) {
    chartTypeBuilder.allowedDefinitionKeys.push("dataSets");
    const getRuntime = chartTypeBuilder.getRuntime;
    chartTypeBuilder.getRuntime = (
        getters,
        definition,
        dataSourceExtractor,
        sheetId,
        eventHandlers
    ) => {
        const isOdoo = definition.dataSource?.type === "odoo";
        if (!isOdoo || !definition.dataSets?.length) {
            return getRuntime(getters, definition, dataSourceExtractor, sheetId, eventHandlers);
        }
        const data = hierarchical.includes(definition.type)
            ? dataSourceExtractor.extractHierarchicalData()
            : dataSourceExtractor.extractData();
        const dataSetStyles = {};
        for (let i = 0; i < data.dataSetsValues.length; i++) {
            const ds = data.dataSetsValues[i];
            const style = definition.dataSets[i];
            dataSetStyles[ds.dataSetId] = style;
        }
        definition = { ...definition, dataSetStyles };
        delete definition.dataSets;
        return getRuntime(getters, definition, dataSourceExtractor, sheetId, eventHandlers);
    };
}
