import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleKanbanRenderer extends KanbanRenderer {
    static template = "sale.SaleKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        SaleActionHelper,
    };
};

