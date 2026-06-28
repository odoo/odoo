import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { IrAttachmentDownload } from "@mail/views/web/attachment/ir_attachment_download";

class IrAttachmentListController extends IrAttachmentDownload(ListController) {}

export const irAttachmentListView = {
    ...listView,
    Controller: IrAttachmentListController,
};

registry.category("views").add("ir_attachment_list", irAttachmentListView);
