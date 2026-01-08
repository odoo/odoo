/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanDropdownMenuWrapper } from "@web/views/kanban/kanban_dropdown_menu_wrapper";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component, useState } from "@odoo/owl";

export class AccountFileUploader extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
        const rec = this.props.record ? this.props.record.data : false;
        this.extraContext = rec ? {
            default_journal_id: rec.id,
            default_move_type: (rec.type === 'sale' && 'out_invoice') || (rec.type === 'purchase' && 'in_invoice') || 'entry',
        } : {};
    }

    async onFileUploaded(file) {
        const att_data = {
            name: file.name,
            mimetype: file.type,
            datas: file.data,
        };
        const [att_id] = await this.orm.create("ir.attachment", [att_data], {
            context: { ...this.extraContext, ...this.env.searchModel.context },
        });
        this.attachmentIdsToProcess.push(att_id);
    }

    async onUploadComplete() {
        let action;
        try {
            action = await this.orm.call(
                "account.journal",
                "create_document_from_attachment",
                ["", this.attachmentIdsToProcess],
                { context: { ...this.extraContext, ...this.env.searchModel.context } },
            );
        } finally {
            // ensures attachments are cleared on success as well as on error
            this.attachmentIdsToProcess = [];
        }
        if (action.context && action.context.notifications) {
            for (let [file, msg] of Object.entries(action.context.notifications)) {
                this.notification.add(
                    msg,
                    {
                        title: file,
                        type: "info",
                        sticky: true,
                    });
            }
            delete action.context.notifications;
        }
        this.action.doAction(action);
    }
}
AccountFileUploader.components = {
    FileUploader,
};
AccountFileUploader.template = "account.AccountFileUploader";
AccountFileUploader.props = {
    ...standardWidgetProps,
    record: { type: Object, optional: true},
    togglerTemplate: { type: String, optional: true },
    btnClass: { type: String, optional: true },
    linkText: { type: String, optional: true },
    slots: { type: Object, optional: true },
};
//when file uploader is used on account.journal (with a record)

export const accountFileUploader = {
    component: AccountFileUploader,
    extractProps: ({ attrs }) => ({
        togglerTemplate: attrs.template || "account.JournalUploadLink",
        btnClass: attrs.btnClass || "",
        linkText: attrs.linkText || attrs.title || _t("Upload"), //TODO: remove linkText attr in master (not translatable)
    }),
    fieldDependencies: [
        { name: "id", type: "integer" },
        { name: "type", type: "selection" },
    ],
};

registry.category("view_widgets").add("account_file_uploader", accountFileUploader);

export class AccountDropZone extends Component {
    setup() {
        this.notificationService = useService("notification");
    }

    onDrop(ev) {
        const selector = '.account_file_uploader.o_input_file';
        // look for the closest uploader Input as it may have a context
        let uploadInput = ev.target.closest('.o_drop_area').parentElement.querySelector(selector) || document.querySelector(selector);
        let files = ev.dataTransfer ? ev.dataTransfer.files : false;
        if (uploadInput && !!files) {
            uploadInput.files = ev.dataTransfer.files;
            uploadInput.dispatchEvent(new Event("change"));
        } else {
            this.notificationService.add(
                _t("Could not upload files"),
                {
                    type: "danger",
                });
        }
        this.props.hideZone();
    }
}
AccountDropZone.props = {
    visible: { type: Boolean, optional: true },
    hideZone: { type: Function, optional: true },
}
AccountDropZone.defaultProps = {
    hideZone: () => {},
};
AccountDropZone.template = "account.DropZone";

// Account Move List View
export class AccountMoveUploadListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.state.dropzoneVisible = false;
    }
}
AccountMoveUploadListRenderer.template = "account.ListRenderer";
AccountMoveUploadListRenderer.components = {
    ...ListRenderer.components,
    AccountDropZone,
};

export class AccountMoveListController extends ListController {
    setup() {
        super.setup();
        this.account_move_service = useService("account_move");
        this.showUploadButton = this.props.context.default_move_type !== 'entry' || 'active_id' in this.props.context;
    }

    async onDeleteSelectedRecords() {
        const selectedResIds = await this.getSelectedResIds();
        if (this.props.resModel !== "account.move" || !await this.account_move_service.addDeletionDialog(this, selectedResIds)) {
            return super.onDeleteSelectedRecords(...arguments);
        }
    }
};

AccountMoveListController.components = {
    ...ListController.components,
    AccountFileUploader,
};

export const AccountMoveUploadListView = {
    ...listView,
    Controller: AccountMoveListController,
    Renderer: AccountMoveUploadListRenderer,
    buttonTemplate: "account.ListView.Buttons",
};

// Account Move Kanban View
export class AccountMoveUploadKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.state.dropzoneVisible = false;
    }
}
AccountMoveUploadKanbanRenderer.template = "account.KanbanRenderer";
AccountMoveUploadKanbanRenderer.components = {
    ...KanbanRenderer.components,
    AccountDropZone,
};

export class AccountMoveUploadKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.showUploadButton = this.props.context.default_move_type !== 'entry' || 'active_id' in this.props.context;
    }
}
AccountMoveUploadKanbanController.components = {
    ...KanbanController.components,
    AccountFileUploader,
};

export const AccountMoveUploadKanbanView = {
    ...kanbanView,
    Controller: AccountMoveUploadKanbanController,
    Renderer: AccountMoveUploadKanbanRenderer,
    buttonTemplate: "account.KanbanView.Buttons",
};

// Accounting Dashboard
export class DashboardKanbanDropdownMenuWrapper extends KanbanDropdownMenuWrapper {
    onClick(ev) {
        // Keep the dropdown open as we need the fileuploader to remain in the dom
        if (!ev.target.tagName === "INPUT" && !ev.target.closest('.file_upload_kanban_action_a')) {
            super.onClick(ev);
        }
    }
}
export class DashboardKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.state = useState({
            dropzoneVisible: false,
        });
    }
}
DashboardKanbanRecord.components = {
    ...DashboardKanbanRecord.components,
    AccountDropZone,
    AccountFileUploader,
    KanbanDropdownMenuWrapper: DashboardKanbanDropdownMenuWrapper,
};
DashboardKanbanRecord.template = "account.DashboardKanbanRecord";

export class DashboardKanbanRenderer extends KanbanRenderer {}
DashboardKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: DashboardKanbanRecord,
};

export const DashboardKanbanView = {
    ...kanbanView,
    Renderer: DashboardKanbanRenderer,
};

registry.category("views").add("account_tree", AccountMoveUploadListView);
registry.category("views").add("account_documents_kanban", AccountMoveUploadKanbanView);
registry.category("views").add("account_dashboard_kanban", DashboardKanbanView);
