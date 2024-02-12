import { click, queryAll, queryFirst } from "@odoo/hoot-dom";

/**
 * @param {RegExp | string} expr
 */
export function getPickerCell(expr) {
    const cells = queryAll(`.o_datetime_picker .o_date_item_cell:contains(${expr})`);
    return cells.length === 1 ? cells[0] : cells;
}

export function getPickerApplyButton() {
    return queryFirst(".o_datetime_picker .o_datetime_buttons .o_apply");
}

export function zoomOut() {
    return click(".o_zoom_out");
}
