import { stores, helpers } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";
const { PivotSidePanelStore } = stores;
const { deepEquals } = helpers;

patch(PivotSidePanelStore.prototype, {
    update(definitionUpdate) {
        const coreDefinition = this.getters.getPivotCoreDefinition(this.pivotId);
        const definition = {
            ...coreDefinition,
            ...this.draft,
            ...definitionUpdate,
        };

        const sortedColumn = definition.sortedColumn;
        if (sortedColumn) {
            if (
                !definition.measures.some(
                    (measure) => measure.fieldName === sortedColumn.measure
                ) ||
                !deepEquals(definition.columns, coreDefinition.columns)
            ) {
                definition.sortedColumn = undefined;
            }
        }
        super.update(definition);
    },
});
