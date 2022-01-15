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
            const activeField = this.model.getActiveField(state);
            actions.items.other.unshift({
                description: state.data[activeField] ? _t('Archive') : _t('Unarchive'),
                callback: () => this._stopRecurrence(state.data['id'], state.data[activeField] ? 'archive' : 'unarchive'),
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

    _stopRecurrence(resId, mode) {
        new Dialog(this, {
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
                            } else if (mode === 'unarchive') {
                                this._toggleArchiveState(false);
                            } else if (mode === 'delete') {
                                this._deleteRecords([this.handle]);
                            }
                        });
                    },
                    close: true,
                    text: _t('Stop Recurrence'),
                },
                {
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_continue_recurrence',
                            args: [resId],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'unarchive') {
                                this._toggleArchiveState(false);
                            } else if (mode === 'delete') {
                                this._deleteRecords([this.handle]);
                            }
                        });
                    },
                    close: true,
                    text: _t('Continue Recurrence'),
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
                text: _t('It seems that this task is part of a recurrence.'),
            }),
        }).open();
    }
});

const FormDescriptionExpanderRenderer = FormRenderer.extend(Object.assign({}, FormHtmlFieldExpanderMixin, {
    // 58px is the sum of the top margin of o_form_sheet 12 px + the bottom padding of o_form_sheet 24px
    // + 5px margin bottom (o_field_widget) + 1px border + the bottom padding of tab-pane 16 px.
    bottomDistance: 58,
}));

export const FormDescriptionExpanderView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Renderer: FormDescriptionExpanderRenderer,
    }),
})

export const ProjectFormView = FormDescriptionExpanderView.extend({
    config: Object.assign({}, FormDescriptionExpanderView.prototype.config, {
        Controller: ProjectFormController,
    }),
});

viewRegistry.add('project_form', ProjectFormView);

viewRegistry.add('form_description_expander', FormDescriptionExpanderView)
