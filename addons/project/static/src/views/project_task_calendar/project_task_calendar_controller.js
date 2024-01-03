/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { subTaskDeleteConfirmationMessage } from "@project/views/project_task_form/project_task_form_controller";
import { ProjectTaskCalendarFilterPanel } from "./project_task_calendar_filter_panel/project_task_calendar_filter_panel";

export class ProjectTaskCalendarController extends CalendarController {
    static components = {
        ...ProjectTaskCalendarController.components,
        FilterPanel: ProjectTaskCalendarFilterPanel,
    };

    get editRecordDefaultDisplayText() {
        return _t("New Task");
    }

    deleteConfirmationDialogProps(record) {
        const deleteConfirmationDialogProps = super.deleteConfirmationDialogProps(record);
        if  (!record.rawRecord.subtask_count) {
            return deleteConfirmationDialogProps;
        }

        return {
            ...deleteConfirmationDialogProps,
            body: subTaskDeleteConfirmationMessage,
        }
    }
}
