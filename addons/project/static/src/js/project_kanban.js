/** @odoo-module **/

import KanbanController from 'web.KanbanController';
import KanbanRenderer from 'web.KanbanRenderer';
import KanbanView from 'web.KanbanView';
import KanbanColumn from 'web.KanbanColumn';
import KanbanRecord from 'web.KanbanRecord';
import KanbanModel from 'web.KanbanModel';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import viewUtils from 'web.viewUtils';

// PROJECTS

const ProjectProjectKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        const kanbanBoxesElement = this.el.querySelectorAll('.o_project_kanban_boxes a');
        if (this.selectionMode !== true && kanbanBoxesElement.length) {
            kanbanBoxesElement[0].click();
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     * @private
     */
    _onManageTogglerClicked: function (event) {
        this._super.apply(this, arguments);
        const thisSettingToggle = this.el.querySelector('.o_kanban_manage_toggle_button');
        this.el.parentNode.querySelectorAll('.o_kanban_manage_toggle_button.show').forEach(el => {
            if (el !== thisSettingToggle) {
                el.classList.remove('show');
            }
        });
        thisSettingToggle.classList.toggle('show');
    },
});

const ProjectProjectKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: ProjectProjectKanbanRecord,
    }),
});

const ProjectProjectKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Renderer: ProjectProjectKanbanRenderer,
    })
});

viewRegistry.add('project_project_kanban', ProjectProjectKanbanView);

// TASKS

const ProjectTaskKanbanColumn = KanbanColumn.extend({
    /**
     * @override
     * @private
     */
    _onDeleteColumn: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_delete_wizard');
    },
});

const ProjectTaskKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: ProjectTaskKanbanColumn,
    }),

    /**
     * Allows record drag when grouping by `personal_stage_type_ids`
     *
     * @override
     */
    _setState() {
        this._super(...arguments);
        const groupedBy = this.state.groupedBy[0];
        const groupByFieldName = viewUtils.getGroupByField(groupedBy);
        const field = this.state.fields[groupByFieldName] || {};
        const fieldInfo = this.state.fieldsInfo.kanban[groupByFieldName] || {};

        const grouped_by_date = ["date", "datetime"].includes(field.type);
        const grouped_by_m2m = field.type === "many2many";
        const readonly = !!field.readonly || !!fieldInfo.readonly;

        const draggable = !readonly && (!grouped_by_m2m || groupByFieldName == 'personal_stage_type_ids') &&
            (!grouped_by_date || fieldInfo.allowGroupRangeValue);

        Object.assign(this.columnOptions, {
            draggable,
        });
    }
});

export const ProjectKanbanController = KanbanController.extend({
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, {
        'kanban_column_delete_wizard': '_onDeleteColumnWizard',
    }),

    _onDeleteColumnWizard: function (ev) {
        ev.stopPropagation();
        const self = this;
        const columnId = ev.target.id;
        const state = this.model.get(this.handle, {raw: true});
        this._rpc({
            model: 'project.task.type',
            method: 'unlink_wizard',
            args: [columnId],
            context: state.getContext(),
        }).then(function (res) {
            self.do_action(res);
        });
    },
});

const ProjectTaskKanbanModel = KanbanModel.extend({

    /**
     * Upon updating `personal_stage_type_ids` we actually want to update the `personal_stage_type_id` field.
     *
     * @override
     * @private
     */
    moveRecord: function (recordID, groupID, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        var new_group = this.localData[groupID];
        var changes = {};
        var groupedFieldName = viewUtils.getGroupByField(parent.groupedBy[0]);
        var groupedField = parent.fields[groupedFieldName];
        // for a date/datetime field, we take the last moment of the group as the group value
        if (['date', 'datetime'].includes(groupedField.type)) {
            changes[groupedFieldName] = viewUtils.getGroupValue(new_group, groupedFieldName);
        } else if (groupedField.type === 'many2one') {
            changes[groupedFieldName] = {
                id: new_group.res_id,
                display_name: new_group.value,
            };
        } else if (groupedField.type === 'selection') {
            var value = _.findWhere(groupedField.selection, {1: new_group.value});
            changes[groupedFieldName] = value && value[0] || false;
        } else if (groupedField.type == 'many2many' && groupedFieldName == 'personal_stage_type_ids') {
            changes['personal_stage_type_id'] = {
                id: new_group.res_id,
                display_name: new_group.value,
            }
        } else {
            changes[groupedFieldName] = new_group.value;
        }

        // Manually updates groups data. Note: this is done before the actual
        // save as it might need to perform a read group in some cases so those
        // updated data might be overridden again.
        var record = self.localData[recordID];
        var resID = record.res_id;
        // Remove record from its current group
        var old_group;
        for (var i = 0; i < parent.data.length; i++) {
            old_group = self.localData[parent.data[i]];
            var index = _.indexOf(old_group.data, recordID);
            if (index >= 0) {
                old_group.data.splice(index, 1);
                old_group.count--;
                if (!old_group.activeFilter || old_group.activeFilter.value === record.data[parent.progressBar.field]) {
                    // Here, the record leaving the old group matches its domain,
                    // so we must decrease the domainCount too.
                    old_group.domainCount--;
                }
                old_group.res_ids = _.without(old_group.res_ids, resID);
                self._updateParentResIDs(old_group);
                break;
            }
        }
        // Add record to its new group
        new_group.data.push(recordID);
        new_group.res_ids.push(resID);
        new_group.count++;

        return this.notifyChanges(recordID, changes).then(function () {
            return self.save(recordID);
        }).then(function () {
            record.parentID = new_group.id;
            return [old_group.id, new_group.id];
        });
    },
})

const ProjectKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: ProjectTaskKanbanModel,
        Controller: ProjectKanbanController,
        Renderer: ProjectTaskKanbanRenderer,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_task_kanban', ProjectKanbanView);
