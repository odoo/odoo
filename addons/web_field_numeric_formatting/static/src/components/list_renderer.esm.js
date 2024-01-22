/* @odoo-module */

import {ListRenderer} from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, "web_field_numeric_formatting.ListRenderer", {
    getFormattedValue(column, record) {
        if (column.options.enable_formatting === false) {
            return record.data[column.name];
        }
        return this._super(...arguments);
    },
});
