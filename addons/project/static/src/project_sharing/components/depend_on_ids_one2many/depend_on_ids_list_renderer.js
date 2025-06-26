/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";

export class DependOnIdsListRenderer extends ListRenderer {
    get nbHiddenRecords() {
        const { context, records } = this.props.list;
        return context.depend_on_count - records.length;
    }
}

DependOnIdsListRenderer.rowsTemplate = "project.DependOnIdsListRowsRenderer";
