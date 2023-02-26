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
import { Domain } from '@web/core/domain';
import view_dialogs from 'web.view_dialogs';
import core from 'web.core';

const _t = core._t;

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
        if (this.groupedBy === 'stage_id') {
            event.preventDefault();
            this.trigger_up('kanban_column_delete_wizard');
        } else {
            this._super(...arguments);
        }
    },

    /**
     * Open alternative view when editing personal stages.
     *
     * @private
     * @override
     */
    _onEditColumn: function (event) {
        if (this.groupedBy !== 'personal_stage_type_ids') {
            this._super(...arguments);
            return;
        }
        event.preventDefault();
        const context = Object.assign({}, this.getSession().user_context, {
            form_view_ref: 'project.personal_task_type_edit',
        });
        new view_dialogs.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            context: context,
            title: _t("Edit Personal Stage"),
            on_saved: this.trigger_up.bind(this, 'reload'),
        }).open();
    },
});

const ProjectTaskKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: ProjectTaskKanbanColumn,
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.isProjectManager = false;
    },

    willStart: function () {
        const superPromise = this._super.apply(this, arguments);

        const isProjectManager = this.getSession().user_has_group('project.group_project_manager').then((hasGroup) => {
            this.isProjectManager = hasGroup;
            this._setState();
            return Promise.resolve();
        });

        return Promise.all([superPromise, isProjectManager]);
    },

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
        const groupedByPersonalStage = (groupByFieldName === 'personal_stage_type_ids');

        const draggable = !readonly && (!grouped_by_m2m || groupedByPersonalStage) &&
            (!grouped_by_date || fieldInfo.allowGroupRangeValue);

        // When grouping by personal stage we allow any project user to create
        let editable = this.columnOptions.editable;
        let deletable = this.columnOptions.deletable;
        if (['stage_id', 'personal_stage_type_ids'].includes(groupByFieldName)) {
            this.groupedByM2O = groupedByPersonalStage || this.groupedByM2O;
            const allow_crud = this.isProjectManager || groupedByPersonalStage;
            this.createColumnEnabled = editable = deletable = allow_crud;
        }

        Object.assign(this.columnOptions, {
            draggable,
            grouped_by_m2o: this.groupedByM2O,
            editable: editable,
            deletable: deletable,
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

    /**
     * @override
     */
    _onDeleteColumn: function (ev) {
        const state = this.model.get(this.handle, {raw: true});
        const groupedByFieldname = state.groupedBy[0];
        if (groupedByFieldname !== 'personal_stage_type_ids') {
            this._super(...arguments);
            return;
        }
        const column = ev.target;
        this._rpc({
            model: 'project.task.type',
            method: 'remove_personal_stage',
            args: [[column.id]],
        }).then(this.update.bind(this, {}, {}));
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
        const self = this;
        const parent = this.localData[parentID];
        const new_group = this.localData[groupID];
        const changes = {};
        const groupedFieldName = viewUtils.getGroupByField(parent.groupedBy[0]);
        const groupedField = parent.fields[groupedFieldName];
        // for a date/datetime field, we take the last moment of the group as the group value
        if (['date', 'datetime'].includes(groupedField.type)) {
            changes[groupedFieldName] = viewUtils.getGroupValue(new_group, groupedFieldName);
        } else if (groupedField.type === 'many2one') {
            changes[groupedFieldName] = {
                id: new_group.res_id,
                display_name: new_group.value,
            };
        } else if (groupedField.type === 'selection') {
            const value = _.findWhere(groupedField.selection, {1: new_group.value});
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
        const record = self.localData[recordID];
        const resID = record.res_id;
        // Remove record from its current group
        let old_group;
        for (let i = 0; i < parent.data.length; i++) {
            old_group = self.localData[parent.data[i]];
            const index = _.indexOf(old_group.data, recordID);
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

    /**
     * When grouped by personal stage create a new personal stage instead of
     * a regular stage.
     * Meaning setting `user_id` on the stage.
     *
     * @override
     */
    createGroup: function (name, parentID) {
        const parent = this.localData[parentID];
        const groupedFieldName = viewUtils.getGroupByField(parent.groupedBy[0]);
        if (groupedFieldName !== 'personal_stage_type_ids') {
            return this._super(...arguments);
        }
        const groupBy = parent.groupedBy[0];
        const context = Object.assign({}, parent.context, {
            default_user_id: this.getSession().uid,
        });
        // In case it's a personal stage we don't want to assign it to the project.
        delete context.default_project_id;
        return this._rpc({
                model: 'project.task.type',
                method: 'name_create',
                args: [name],
                context: context,
            })
            .then((result) => {
                const createGroupDataPoint = (model, parent) => {
                    const newGroup = model._makeDataPoint({
                        modelName: parent.model,
                        context: parent.context,
                        domain: parent.domain.concat([[groupBy, "=", result[0]]]),
                        fields: parent.fields,
                        fieldsInfo: parent.fieldsInfo,
                        isOpen: true,
                        limit: parent.limit,
                        parentID: parent.id,
                        openGroupByDefault: true,
                        orderedBy: parent.orderedBy,
                        value: result,
                        viewType: parent.viewType,
                    });
                    if (parent.progressBar) {
                        newGroup.progressBarValues = _.extend({
                            counts: {},
                        }, parent.progressBar);
                    }
                    return newGroup;
                };
                const newGroup = createGroupDataPoint(this, parent);
                parent.data.push(newGroup.id);
                if (this.isInSampleMode()) {
                    // in sample mode, create the new group in both models (main + sample)
                    const sampleParent = this.sampleModel.localData[parentID];
                    const newSampleGroup = createGroupDataPoint(this.sampleModel, sampleParent);
                    sampleParent.data.push(newSampleGroup.id);
                }
                return newGroup.id;
            });
    },

    /**
     * Force tasks assigned to the user when grouping by personal stage.
     *
     * @override
     * @private
     */
    _readGroup: function (list) {
        const groupedBy = list.groupedBy[0];
        if (groupedBy === 'personal_stage_type_ids') {
            list.domain = Domain.and([
                [['user_ids', 'in', this.getSession().uid]],
                list.domain
            ]).toList();
        }
        return this._super(...arguments);
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
