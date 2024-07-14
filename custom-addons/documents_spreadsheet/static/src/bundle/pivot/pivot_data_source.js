/** @odoo-module */

import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import { patch } from "@web/core/utils/patch";

patch(PivotDataSource.prototype, {
    /**
     * @param {string} fieldName
     */
    getPossibleValuesForGroupBy(fieldName) {
        this._assertDataIsLoaded();
        return this._model.getPossibleValuesForGroupBy(fieldName);
    },
});
