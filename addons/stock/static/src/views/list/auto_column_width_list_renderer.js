/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

export class AutoColumnWidthListRenderer extends ListRenderer {
    static props = [...ListRenderer.props];
    static useMagicColumnWidths = false;
}
