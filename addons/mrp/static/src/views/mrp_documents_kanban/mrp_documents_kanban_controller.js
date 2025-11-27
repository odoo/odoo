import { KanbanController } from "@web/views/kanban/kanban_controller";
import { UploadButton } from "@product/js/product_document_kanban/upload_button/upload_button";

export class MrpDocumentsKanbanController extends KanbanController {
    static components = { ...KanbanController.components, UploadButton };

    setup() {
        super.setup();
        this.uploadRoute = '/mrp/document/upload';
        this.formData = {
            'res_model': this.props.context.default_res_model,
            'res_id': this.props.context.default_res_id,
        };
    }
}
