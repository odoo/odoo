/** @odoo-module **/

import Dialog from 'web.Dialog';
import FormView from 'web.FormView';
import FormController from 'web.FormController';
import { bus, _t } from 'web.core';
import { device } from 'web.config';
import viewRegistry from 'web.view_registry';

const ProjectFormController = FormController.extend({
    on_attach_callback() {
        this._super(...arguments);
        if (!device.isMobile) {
            bus.on("DOM_updated", this, this._onDomUpdated);
        }
    },
    _onDomUpdated() {
        const $editable = this.$el.find('.note-editable');
        if ($editable.length) {
            const minHeight = window.innerHeight - $editable.offset().top - 42;
            $editable.css('min-height', minHeight + 'px');
        }
    },
    on_detach_callback() {
        this._super(...arguments);
        bus.off('DOM_updated', this._onDomUpdated);
    },
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
            : _t('It seems that this task is part of a recurrence. You must keep it as a model to create the next occurences.');
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
                            } else if (mode === 'unarchive') {
                                this._toggleArchiveState(false);
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
    }
});

export const ProjectFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ProjectFormController,
    }),
});

viewRegistry.add('project_form', ProjectFormView);
