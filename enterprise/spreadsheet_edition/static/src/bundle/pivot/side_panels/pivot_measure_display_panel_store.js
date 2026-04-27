import { stores } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { PivotMeasureDisplayPanelStore } = stores;

patch(PivotMeasureDisplayPanelStore.prototype, {
    get fields() {
        try {
            return super.fields;
        } catch {
            return [];
        }
    },
    getPossibleValues(fieldNameWithGranularity) {
        try {
            return super.getPossibleValues(fieldNameWithGranularity);
        } catch {
            return [];
        }
    },
});
