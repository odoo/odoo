/** @odoo-module */

import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class ProjectTaskKanbanHeader extends KanbanHeader {
    editGroup() {
        const { resModel, value } = this.group;
        const groupBy = this.props.list.groupBy;
        if (groupBy.length !== 1 || groupBy[0] !== 'personal_stage_type_ids') {
            super.editGroup();
            return;
        }
        const context = Object.assign({}, this.group.context, {
            form_view_ref: 'project.personal_task_type_edit',
        });
        this.dialog.add(FormViewDialog, {
            context,
            resId: value,
            resModel: resModel,
            title: this.env._t('Edit Personal Stage'),
            onRecordSaved: async () => {
                await this.props.list.load();
                this.props.list.model.notify();
            },
        });
    }
}
