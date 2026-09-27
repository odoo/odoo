import { t, useProps } from "@odoo/owl";
import { KanbanRecord, kanbanRecordProps } from "@web/views/kanban/kanban_record";

export class SurveyKanbanRecord extends KanbanRecord {
    props = useProps({
        ...kanbanRecordProps,
        isGrouped: t.any().optional(false),
    });

    get renderingContext() {
        return {
            ...super.renderingContext,
            isGrouped: this.props.isGrouped,
        };
    }
}
