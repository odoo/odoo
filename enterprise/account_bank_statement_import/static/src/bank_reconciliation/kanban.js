/** @odoo-module **/
import { registry } from "@web/core/registry";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";
import { UploadDropZone } from "@account/components/upload_drop_zone/upload_drop_zone";
import { BankRecKanbanView, BankRecKanbanController, BankRecKanbanRenderer } from "@account_accountant/components/bank_reconciliation/kanban";
import { useState } from "@odoo/owl";

export class BankRecKanbanUploadController extends BankRecKanbanController {
    static components = {
        ...BankRecKanbanController.components,
        AccountFileUploader,
    }
}

export class BankRecUploadKanbanRenderer extends BankRecKanbanRenderer {
    static template = "account.BankRecKanbanUploadRenderer";
    static components = {
        ...BankRecKanbanRenderer.components,
        UploadDropZone,
    };
    setup() {
        super.setup();
        this.dropzoneState = useState({
            visible: false,
        });
    }

    onDragStart(ev) {
        if (ev.dataTransfer.types.includes("Files")) {
            this.dropzoneState.visible = true
        }
    }
}

export const BankRecKanbanUploadView = {
    ...BankRecKanbanView,
    Controller: BankRecKanbanUploadController,
    Renderer: BankRecUploadKanbanRenderer,
    buttonTemplate: "account.BankRecKanbanButtons",
};

registry.category("views").add('bank_rec_widget_kanban', BankRecKanbanUploadView, { force: true });
