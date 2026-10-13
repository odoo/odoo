import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { ProductCatalogKanbanRecord } from "./kanban_record";

export class ProductCatalogKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ProductCatalogKanbanRecord,
    };
}
