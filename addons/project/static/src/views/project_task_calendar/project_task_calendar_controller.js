import { _t } from "@web/core/l10n/translation";
import { unique } from "@web/core/utils/arrays";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { subTaskDeleteConfirmationMessage } from "@project/views/project_task_form/project_task_form_controller";

import { ProjectTaskCalendarSidePanel } from "./side_panel/project_task_calendar_side_panel";

export class ProjectTaskCalendarController extends CalendarController {
    static components = {
        ...ProjectTaskCalendarController.components,
        CalendarSidePanel: ProjectTaskCalendarSidePanel,
    };

    get modelParams() {
        const modelParams = super.modelParams;
        // add the `state` field to the list of fields to read as we need it
        // to compute the `o_past_event` classname
        const fieldNames = unique(modelParams.fieldNames.concat(["state"]));
        return { ...modelParams, fieldNames };
    }

    get editRecordDefaultDisplayText() {
        return _t("New Task");
    }

    /**
     * @override
     */
    get canScheduleEvents() {
        return super.canScheduleEvents && Boolean(this.props.context.default_project_id);
    }

    deleteConfirmationDialogProps(record) {
        const deleteConfirmationDialogProps = super.deleteConfirmationDialogProps(record);
        if (!record.rawRecord.subtask_count) {
            return deleteConfirmationDialogProps;
        }

        return {
            ...deleteConfirmationDialogProps,
            body: subTaskDeleteConfirmationMessage,
        };
    }
}
