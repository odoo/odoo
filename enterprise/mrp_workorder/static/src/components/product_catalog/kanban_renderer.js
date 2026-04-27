/** @odoo-module **/

import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

patch(ProductCatalogKanbanRenderer, {
    props: [...KanbanRenderer.props, "pushCatalogKanbanUpdate?"],
});
