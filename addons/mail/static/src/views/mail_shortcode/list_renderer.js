/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

export class MailShortcodeListRenderer extends ListRenderer {
    getFormattedValue(column, record) {
        const format_value = super.getFormattedValue(column, record);
        if (column.name == "source") {
            return `:${format_value}`;
        }
        return format_value;
    }
}
