import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { FileUploadKanbanRenderer } from "@account/views/file_upload_kanban/file_upload_kanban_renderer";
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleKanbanRenderer extends FileUploadKanbanRenderer {
    static template = "sale.SaleKanbanRenderer";
    static components = {
        ...FileUploadKanbanRenderer.components,
        SaleActionHelper,
    };

    onDragStart(ev) {
        super.onDragStart(ev);
        this.dropzoneState.dropzoneDescriptionText = markup(_t(`
            <h2 class="mt-4 text-white fw-bold">Import request for quotation from a customer</h2>
            <span class="mt-4 text-white fw-bold">
                If your customer runs on Odoo 18 or higher, customer data and 
                sales order lines will be automatically created. Any other pdf 
                containing an attached UBL-ReequestForQutoation file will work as well.
            </span>
            `))
    }
};
