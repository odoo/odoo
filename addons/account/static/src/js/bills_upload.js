/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { FileUploader } from "@web/views/fields/file_handler";

const { Component, useState } = owl;

class AccountFileUploader extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.attachment_ids_to_process = [];
    }

    async onFileUploaded(file) {
        let att_data = {
            name: file.name,
            mimetype: file.type,
            datas: file.data,
        }
        const att_id = await this.orm.call("ir.attachment", "create", [att_data], {
            context: {...this.props.extraContext, ...this.env.searchModel.context},
        });
        this.attachment_ids_to_process.push(att_id);
    }

    async onUploadComplete() {
        const action = await this.orm.call("account.journal", "create_document_from_attachment", ["", this.attachment_ids_to_process], {
            context: {...this.props.extraContext, ...this.env.searchModel.context},
        });
        this.attachment_ids_to_process = [];
        this.action.doAction(action);
    }
}
AccountFileUploader.components = {
    FileUploader,
}
AccountFileUploader.template = "account.HiddenFileUploader";

class AccountDropZone extends Component {}
AccountDropZone.defaultProps = {
    visibilityClass: "d-none",
    dragOver: () => {},
    dragLeave: () => {},
    drop: () => {},
}
AccountDropZone.template = "account.DropZone";

const AccountMoveDropzoneFunctions = {
    setupDropZone() {
        this.notificationService = useService("notification");
        this.dzState = useState({
            dzClass: "d-none",
        })
    },

    showDropZone(ev) {
        this.dzState.dzClass = "";
    },

    hideDropZone(ev) {
        this.dzState.dzClass = "d-none";
    },

    onDrop(ev) {
        const selector = '.account_file_uploader.o_input_file.o_hidden';
        let uploadInput = ev.target.closest('.o_drop_area').querySelector(selector) || document.querySelector(selector);
        let files = ev.dataTransfer ? ev.dataTransfer.files : false;
        ev.preventDefault();
        if (!!uploadInput && files) {
            uploadInput.files = ev.dataTransfer.files;
            uploadInput.dispatchEvent(new Event("change"));
        } else {
            this.notificationService.add(
                this.env._t("Could not upload files"),
                {
                    type: "danger",
                });
        }
        this.hideDropZone();
    },
}

// Account Move List View
class AccountMoveUploadListRenderer extends ListRenderer {
    setup() {
        super.setup();
        Object.assign(this, AccountMoveDropzoneFunctions);
        this.setupDropZone();
    }
}
AccountMoveUploadListRenderer.template = "account.ListRenderer";
AccountMoveUploadListRenderer.components = {
    ...ListRenderer.components,
    AccountDropZone,
};

ListController.components = {
    ...ListController.components,
    AccountFileUploader,
}

const AccountMoveUploadListView = {
    ...listView,
    Renderer: AccountMoveUploadListRenderer,
    buttonTemplate: "account.ListView.Buttons",
};

// Account Move Kanban View
class AccountMoveUploadKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        Object.assign(this, AccountMoveDropzoneFunctions);
        this.setupDropZone();
    }
}
AccountMoveUploadKanbanRenderer.template = "account.KanbanRenderer";
AccountMoveUploadKanbanRenderer.components = {
    ...KanbanRenderer.components,
    AccountDropZone
};

KanbanController.components = {
    ...KanbanController.components,
    AccountFileUploader
};

const AccountMoveUploadKanbanView = {
    ...kanbanView,
    Renderer: AccountMoveUploadKanbanRenderer,
    buttonTemplate: "account.KanbanView.Buttons",
};

// Accounting Dashboard
class DashboardKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        Object.assign(this, AccountMoveDropzoneFunctions);
        this.setupDropZone();
    }
}
DashboardKanbanRecord.components = {
    ...DashboardKanbanRecord.components,
    AccountDropZone,
    AccountFileUploader,
}
DashboardKanbanRecord.template = "account.DashboardKanbanRecord";

class DashboardKanbanRenderer extends KanbanRenderer {}
DashboardKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: DashboardKanbanRecord,
};

const DashboardKanbanView = {
    ...kanbanView,
    Renderer: DashboardKanbanRenderer,
}

registry.category("views").add("account_tree", AccountMoveUploadListView);
registry.category("views").add("account_documents_kanban", AccountMoveUploadKanbanView);
registry.category("views").add("account_dashboard_kanban", DashboardKanbanView);
