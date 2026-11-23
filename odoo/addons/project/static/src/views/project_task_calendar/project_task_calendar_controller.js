/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ProjectTaskCalendarFilterPanel } from "./project_task_calendar_filter_panel/project_task_calendar_filter_panel";
import { DeleteSubtasksConfirmationDialog } from "@project/components/delete_subtasks_confirmation_dialog/delete_subtasks_confirmation_dialog";

export class ProjectTaskCalendarController extends CalendarController {
    static components = {
        ...ProjectTaskCalendarController.components,
        FilterPanel: ProjectTaskCalendarFilterPanel,
    };
    setup() {
        super.setup(...arguments);
        this.env.config.setDisplayName(this.env.config.getDisplayName() + _t(" - Tasks by Deadline"));
    }

    get editRecordDefaultDisplayText() {
        return _t("New Task");
    }

    deleteRecord(record) {
        if  (!record.rawRecord.subtask_count) {
            return super.deleteRecord(record);
        }
        this.displayDialog(DeleteSubtasksConfirmationDialog, {
            confirm: () => {
                this.model.unlinkRecord(record.id);
            },
        });
    }
}
