import { FileUploadKanbanRenderer } from "@account/views/file_upload_kanban/file_upload_kanban_renderer";
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleKanbanRenderer extends FileUploadKanbanRenderer {
    static template = "sale.SaleKanbanRenderer";
    static components = {
        ...FileUploadKanbanRenderer.components,
        SaleActionHelper,
    };
};

