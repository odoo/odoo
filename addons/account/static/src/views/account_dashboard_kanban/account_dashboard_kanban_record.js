import { user } from "@web/core/user";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";
import { UploadDropZone } from "@account/components/upload_drop_zone/upload_drop_zone";
import { KanbanDropdownMenuWrapper } from "@web/views/kanban/kanban_dropdown_menu_wrapper";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

import { useState, onWillStart } from "@odoo/owl";

// Accounting Dashboard
export class DashboardKanbanDropdownMenuWrapper extends KanbanDropdownMenuWrapper {
    onClick(ev) {
        // Keep the dropdown open as we need the fileupload to remain in the dom
        if (!ev.target.tagName === "INPUT" && !ev.target.closest('.file_upload_kanban_action_a')) {
            super.onClick(ev);
        }
    }
}

export class DashboardKanbanRecord extends KanbanRecord {
    static template = "account.DashboardKanbanRecord";
    static components = {
        ...DashboardKanbanRecord.components,
        UploadDropZone,
        AccountFileUploader,
        KanbanDropdownMenuWrapper: DashboardKanbanDropdownMenuWrapper,
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.allowDrop = this.recordDropSettings.group ? await user.hasGroup(this.recordDropSettings.group) : true;
        });
        this.dropzoneState = useState({
            visible: false,
        });
    }

    get recordDropSettings() {
        const kanbanDashboard = JSON.parse(this.props.record.data.kanban_dashboard);
        return {
            image: kanbanDashboard.drag_drop_settings.image,
            text: kanbanDashboard.drag_drop_settings.text,
            company_name: kanbanDashboard.company_name,
            show_company: kanbanDashboard.show_company
        };
    }

    get dropzoneProps() {
        const recordDropSettings = this.recordDropSettings;
        return {
            visible: this.dropzoneState.visible,
            dragIcon: recordDropSettings.image,
            dragText: recordDropSettings.text,
            dragCompany: recordDropSettings.company_name,
            dragShowCompany: recordDropSettings.show_company,
            dragTitle: this.props.record.data.name,
            hideZone: () => { this.dropzoneState.visible = false; },
        }
    }
}
