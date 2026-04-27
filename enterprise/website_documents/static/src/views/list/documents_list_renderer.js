import { DocumentsListRenderer } from "@documents/views/list/documents_list_renderer";
import { patch } from "@web/core/utils/patch";

patch(DocumentsListRenderer.prototype, {

    get editableColumns() {
        return super.editableColumns.concat(["website_id"]);
    }

});
