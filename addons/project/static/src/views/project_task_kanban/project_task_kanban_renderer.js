/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { Record } from '@web/views/record';
import { registry } from '@web/core/registry';

const { onWillStart } = owl;

export class ProjectTaskKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.userService = useService('user');
        this.action = useService('action');

        this.isProjectManager = false;
        onWillStart(this.onWillStart);
    }

    get canMoveRecords() {
        let canMoveRecords = super.canMoveRecords;
        if (!canMoveRecords && this.canResequenceRecords && this.props.list.isGroupedByPersonalStages) {
            const { groupByField } = this.props.list;
            const { modifiers } = groupByField;
            canMoveRecords = !(modifiers && modifiers.readonly);
        }
        return canMoveRecords;
    }

    get canResequenceGroups() {
        let canResequenceGroups = super.canResequenceGroups;
        if (!canResequenceGroups && this.props.list.isGroupedByPersonalStages) {
            const { modifiers } = this.props.list.groupByField;
            const { groupsDraggable } = this.props.archInfo;
            canResequenceGroups = groupsDraggable && !(modifiers && modifiers.readonly);
        }
        return canResequenceGroups;
    }

    async onWillStart() {
        if (!this.props.list.isGroupedByPersonalStages) { // no need to check it if the group by is personal stages
            this.isProjectManager = await this.userService.hasGroup('project.group_project_manager');
        }
    }

    canCreateGroup() {
        return super.canCreateGroup() && (!this.props.list.isGroupedByStage || this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
    }

    canDeleteGroup(group) {
        return super.canDeleteGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
    }

    canEditGroup(group) {
        return super.canEditGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
    }

    async deleteGroup(group) {
        if (group && group.groupByField.name === 'stage_id') {
            const action = await group.model.orm.call(
                group.resModel,
                'unlink_wizard',
                [group.resId],
                { context: group.context },
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup(group);
    }

    editGroup(group) {
        const groupBy = this.props.list.groupBy;
        if (groupBy.length !== 1 || groupBy[0] !== 'personal_stage_type_ids') {
            super.editGroup(group);
            return;
        }
        const context = Object.assign({}, group.context, {
            form_view_ref: 'project.personal_task_type_edit',
        });
        this.dialog.add(FormViewDialog, {
            context,
            resId: group.value,
            resModel: group.resModel,
            title: this.env._t('Edit Personal Stage'),
            onRecordSaved: async () => {
                await this.props.list.load();
                this.props.list.model.notify();
            },
        });
    }
}

class ProutRecord extends owl.Component {

    setup() {
        this.state = owl.useState({folded: true});
    }

    get fieldsInfo() {
        return {
            child_ids: {
                type: "one2many",
                relation: "project.task",
                fieldsToFetch: {
                    display_name: { type: "char" },
                }
            }
        }
    }

    get values() {
        return {
            child_ids: this.props.record.data.child_ids.currentIds,
        }
    }
}
ProutRecord.components = { Record };
ProutRecord.template = owl.xml`
<a class="btn-primary" t-on-click="() => state.folded = !state.folded" >Prout</a>
<Record t-if="!state.folded" resModel="'project.task'" fields="fieldsInfo" activeFields="fieldsInfo" values="values" t-slot-scope="data">
    <t t-foreach="data.record.data.child_ids.records" t-as="subTask" t-key="subTask.resId">
        <p t-esc="subTask.data.display_name" />
    </t>
</Record>
`
ProutRecord.fieldDependencies = { child_ids: { type: "one2many"}}

registry.category("view_widgets").add("project_asana", ProutRecord);
