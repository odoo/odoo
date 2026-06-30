import { UploadButton } from '@product/js/product_document_kanban/upload_button/upload_button';
import { KanbanController } from '@web/views/kanban/kanban_controller';

export class ProductDocumentKanbanController extends KanbanController {
    static components = { ...KanbanController.components, UploadButton };

    setup() {
        super.setup();
        this.uploadRoute = '/product/document/upload';
        this.formData = {
            'res_model': this.props.context.default_res_model,
            'res_id': this.props.context.default_res_id,
        };
    }
}
