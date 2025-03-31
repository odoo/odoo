import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { RecruitmentActionHelper } from "@hr_recruitment/views/recruitment_helper_view";

export class RecruitmentKanbanRenderer extends KanbanRenderer {
    static template = "hr_recruitment.RecruitmentKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        RecruitmentActionHelper,
    };

    async archiveRecord(record, active) {
        if (active && record.data.application_count > 0) {
            this.dialog.add(ConfirmationDialog, {
                body: _t(
                    "This job position and all related applicants will be archived. Are you sure?"
                ),
                confirmLabel: _t("Archive"),
                confirm: () => {
                    record.archive();
                    this.props.list.load();
                },
                cancel: () => {},
            });
        } else if (active) {
            record.archive();
            this.props.list.load();
        } else {
            record.unarchive();
            this.props.list.load();
        }
    }
}

export const RecruitmentKanbanView = {
    ...kanbanView,
    Renderer: RecruitmentKanbanRenderer,
};

registry.category("views").add("recruitment_kanban_view", RecruitmentKanbanView);
