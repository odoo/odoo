odoo.define('project.ProjectFormView', function (require) {
    "use strict";

    const Dialog = require('web.Dialog');
    const FormView = require('web.FormView');
    const FormController = require('web.FormController');
    const core = require('web.core');
    const view_registry = require('web.view_registry');

    const _t = core._t;

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
                    callback: () => this._stopRecurrence(state.data['id'], state.data[activeField]?'archive':'unarchive'),
                });
            }

            return actions;
        },

        _onDeleteRecord() {
            const record = this.model.get(this.handle);
            
            if(!record.data.recurrence_id) {
                return this._super(...arguments);
            }
            this._stopRecurrence(record.res_id, 'delete');
        },

        _stopRecurrence(res_id, mode) {
            new Dialog(this, {
                buttons: [
                    {
                        classes: 'btn-primary',
                        click: () => {
                            this._rpc({
                                model: 'project.task',
                                method: 'action_stop_recurrence',
                                args: [res_id],
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
                                args: [res_id],
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
    
    const ProjectFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: ProjectFormController,
        }),
    });

    view_registry.add('project_form', ProjectFormView);

    return ProjectFormView;
});
