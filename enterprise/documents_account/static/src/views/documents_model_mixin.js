import { DocumentsKanbanModel } from "@documents/views/kanban/documents_kanban_model";
import { DocumentsListModel } from "@documents/views/list/documents_list_model";
import { patch } from "@web/core/utils/patch";

export const AccountIsViewablePatch = {
    /**
     * @override
     */
    isViewable() {
        if (this.data.mimetype.endsWith("/xml") && this.data.has_embedded_pdf) {
            return true;
        }
        return super.isViewable(...arguments);
    },
};

patch(DocumentsKanbanModel.Record.prototype, AccountIsViewablePatch);
patch(DocumentsListModel.Record.prototype, AccountIsViewablePatch);
