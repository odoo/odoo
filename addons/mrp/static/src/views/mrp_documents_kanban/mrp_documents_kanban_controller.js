/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductDocumentKanbanController } from "@product/js/product_document_kanban/product_document_kanban_controller";

patch(ProductDocumentKanbanController.prototype, {
    buildFormData(formData) {
        super.buildFormData(formData);
        if (this.props.context.attached_on_bom) {
            formData.append("attached_on_bom", this.props.context.bom_id);
        }
    },
});
