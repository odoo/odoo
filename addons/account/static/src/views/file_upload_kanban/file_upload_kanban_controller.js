import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DocumentFileUploader } from "@account/components/document_file_uploader/document_file_uploader";

export class FileUploadKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
        DocumentFileUploader,
    };
}
