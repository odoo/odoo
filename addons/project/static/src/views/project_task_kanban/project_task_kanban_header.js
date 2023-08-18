/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { onWillStart } from "@odoo/owl";

export class ProjectTaskKanbanHeader extends KanbanHeader {
    setup() {
        super.setup();
        this.action = useService('action');
        this.userService = useService('user');

        this.isProjectManager = false;
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        if (!this.props.list.isGroupedByPersonalStages) { // no need to check it if the group by is personal stages
            this.isProjectManager = await this.userService.hasGroup('project.group_project_manager');
        }
    }

    editGroup() {
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
            resId: this.group.value,
            resModel: this.group.groupByField.relation,
            title: _t('Edit Personal Stage'),
            onRecordSaved: async () => {
                await this.props.list.load();
            },
        });
    }

    async deleteGroup() {
        if (this.group.groupByField.name === 'stage_id') {
            const action = await this.group.model.orm.call(
                this.group.groupByField.relation,
                'unlink_wizard',
                [this.group.value],
                { context: this.group.context },
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup();
    }

    canEditGroup(group) {
        return super.canEditGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
    }

    canDeleteGroup(group) {
        return super.canDeleteGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
    }

    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "project_id") {
            return _t("🔒 Private");
        } else if (fieldName === "user_ids") {
            return _t("👤 Unassigned");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
