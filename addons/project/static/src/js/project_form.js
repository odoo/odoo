/** @odoo-module **/

import Dialog from 'web.Dialog';
import FormView from 'web.FormView';
import FormController from 'web.FormController';
import FormRenderer from 'web.FormRenderer';
import { _t } from 'web.core';
import viewRegistry from 'web.view_registry';
import FormHtmlFieldExpanderMixin from './project_form_html_field_expander_mixin'

const ProjectFormController = FormController.extend({
    _getActionMenuItems(state) {
        if (!this.archiveEnabled || !state.data['recurrence_id']) {
            return this._super(...arguments);
        }

        this.archiveEnabled = false;
        let actions = this._super(...arguments);
        this.archiveEnabled = true;

        if (actions) {
            actions.items.other.unshift({
                description: _t('Archive'),
                callback: () => this._stopRecurrence(state.data['id'], 'archive'),
            });
        }

        return actions;
    },

    _onDeleteRecord() {
        const record = this.model.get(this.handle);

        if (!record.data.recurrence_id) {
            return this._super(...arguments);
        }
        this._stopRecurrence(record.res_id, 'delete');
    },

    _countTasks(recurrence_id) {
        return this._rpc({
            model: 'project.task',
            method: 'search_count',
            args: [[["recurrence_id", "=", recurrence_id.res_id]]],
        });
    },

    async _stopRecurrence(resId, mode) {
        const record = this.model.get(this.handle);
        const recurrence_id = record.data.recurrence_id;
        const count = await this._countTasks(recurrence_id);
        const allowContinue = count != 1;

        const alert = allowContinue
            ? _t('It seems that this task is part of a recurrence.')
            : _t('It seems that this task is recurrent. Would you like to stop its recurrence?');
        const dialog = new Dialog(this, {
            buttons: [
                {
                    classes: 'btn-primary',
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_stop_recurrence',
                            args: [resId],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords([this.handle]);
                            }
                        });
                    },
                    close: true,
                    text: _t('Stop Recurrence'),
                },
                {
                    close: true,
                    text: _t('Discard'),
                }
            ],
            size: 'medium',
            title: _t('Confirmation'),
            $content: $('<main/>', {
                role: 'alert',
                text: alert,
            }),
        });

        if (allowContinue) {
            dialog.buttons.splice(1, 0,
                {
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_continue_recurrence',
                            args: [resId],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords([this.handle]);
                            }
                        });
                    },
                    close: true,
                    text: _t('Continue Recurrence'),
                })
        };

        dialog.open();
    },

    async _applyChanges(dataPointID, changes, event) {
        const result = await this._super(...arguments);
        if (event.data.force_save && 'stage_id' in changes) {
            this._getMilestoneReachWizardAction([parseInt(event.target.res_id)]);
        }
        return result;
    },
    async _getMilestoneReachWizardAction(recordIds) {
        const action = await this._rpc({
            model: 'project.task',
            method: 'get_milestone_to_mark_as_reached_action',
            args: [recordIds],
        });
        if (action) {
            this.trigger_up('do-action', {
                action,
            });
        }
    },
    async _saveRecord(recordID, options) {
        const task = this.model.get(recordID || this.handle);
        const result = await this._super(...arguments);
        // --test-tags /industry_fsm.test_ui
        // <page name="task_dependencies" groups="project.group_project_task_dependencies"></page>
        let tasksX2ManyFields = Object.keys(task.data).filter(fieldName => ['child_ids', 'depend_on_ids'].includes(fieldName));
        if (tasksX2ManyFields.length) {
            const taskResIds = [];
            for (const taskX2ManyFieldName of tasksX2ManyFields) {
                for (const subtask of task.data[taskX2ManyFieldName].data) {
                    const changes = this.model.localData[subtask.id]._changes;
                    if (changes && changes.hasOwnProperty('stage_id') && !!subtask.data.milestone_id) {
                        taskResIds.push(subtask.res_id);
                    }
                }
            }
            if (taskResIds.length) {
                this._getMilestoneReachWizardAction(taskResIds);
            }
        }
        return result;
    },
});

const FormDescriptionExpanderRenderer = FormRenderer.extend(Object.assign({}, FormHtmlFieldExpanderMixin, {
    // 58px is the sum of the top margin of o_form_sheet 12 px + the bottom padding of o_form_sheet 24px
    // + 5px margin bottom (o_field_widget) + 1px border + the bottom padding of tab-pane 16 px.
    bottomDistance: 58,
    fieldQuerySelector: '.o_xxl_form_view .oe_form_field.oe_form_field_html[name="description"]',
}));

export const FormDescriptionExpanderView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Renderer: FormDescriptionExpanderRenderer,
    }),
})

export const ProjectFormRenderer = FormDescriptionExpanderRenderer.extend({
    /**
     * @private
     * @override
     */
    _renderStatButton: function (node) {
        const $button = this._super.apply(this, arguments);
        if ($button.attr('name') == 'action_open_parent_task' && this.state.data.parent_id) {
            $button.prop('title', this.state.data.parent_id.data.display_name);
        }
        return $button;
    },
})

export const ProjectFormView = FormDescriptionExpanderView.extend({
    config: Object.assign({}, FormDescriptionExpanderView.prototype.config, {
        Controller: ProjectFormController,
        Renderer: ProjectFormRenderer,
    }),
});

viewRegistry.add('project_form', ProjectFormView);

viewRegistry.add('form_description_expander', FormDescriptionExpanderView)
