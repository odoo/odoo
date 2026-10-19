import { FileUploadKanbanController } from "../file_upload_kanban/file_upload_kanban_controller";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";

export class AccountMoveKanbanController extends FileUploadKanbanController {
    static components = {
        ...FileUploadKanbanController.components,
        AccountFileUploader,
    };

    setup() {
        super.setup();
        this.showUploadButton = this.props.context.default_move_type !== 'entry' || 'active_id' in this.props.context;
    }
}
