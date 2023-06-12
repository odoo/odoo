/** @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class HrRecruitmentKanbanHeader extends KanbanHeader {
    deleteGroup() {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Recruitment stages can't be deleted for reporting purposes. Fold the stage instead."),
            confirm: () => {},
        });
    }
}

export class HrRecruitmentKanbanRenderer extends KanbanRenderer {}
KanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanHeader: HrRecruitmentKanbanHeader,
}
    
