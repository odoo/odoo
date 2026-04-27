import { DocumentsListController } from "@documents/views/list/documents_list_controller";
import { patch } from "@web/core/utils/patch";

patch(DocumentsListController.prototype, {

    get internalOnlyColumns() {
        return super.internalOnlyColumns.concat(["website_id"]);
    }

});
