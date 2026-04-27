/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";

import { NewReportDialog } from "./new_report_dialog";

class StudioReportKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }
    createRecord() {
        this.dialogService.add(NewReportDialog, {
            resModel: this.props.context.default_model,
            onReportCreated: (report) => {
                this.openRecord({ data: report, resId: report.id });
            },
        });
    }

    openRecord(record) {
        return this.actionService.doAction("web_studio.action_edit_report", {
            report: {
                data: record.data,
                res_id: record.resId,
            },
        });
    }
}

const studioReportKanbanView = {
    ...kanbanView,
    Controller: StudioReportKanbanController,
};

registry.category("views").add("studio_report_kanban", studioReportKanbanView);
