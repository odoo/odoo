/** @odoo-module **/

import { _t } from 'web.core';
import Dialog from 'web.Dialog';
import ListView from 'web.ListView';
import ListController from 'web.ListController';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';

const ProjectListController = ListController.extend({
    _getActionMenuItems(state) {
        if (!this.archiveEnabled) {
            return this._super(...arguments);
        }

        const recurringRecords = this.getSelectedRecords().filter(rec => rec.data.recurrence_id).map(rec => rec.data.id);
        this.archiveEnabled = recurringRecords.length == 0;
        let actions = this._super(...arguments);
        this.archiveEnabled = true;

        if (actions && recurringRecords.length > 0) {
            actions.items.other.unshift({
                description: _t('Archive'),
                callback: () => this._stopRecurrence(recurringRecords, this.selectedRecords, 'archive'),
            }, {
                description: _t('Unarchive'),
                callback: () => this._toggleArchiveState(false)
            });
        }
        return actions;
    },

    _onDeleteSelectedRecords() {
        const recurringRecords = this.getSelectedRecords().filter(rec => rec.data.recurrence_id).map(rec => rec.data.id);
        if (recurringRecords.length > 0) {
            return this._stopRecurrence(recurringRecords, this.selectedRecords, 'delete');
        }

        return this._super(...arguments);
    },

    _stopRecurrence(recurringResIds, resIds, mode) {
        let warning;
        if (resIds.length > 1) {
            warning = _t('It seems that some tasks are part of a recurrence.');
        } else {
            warning = _t('It seems that this task is part of a recurrence.');
        }
        return new Dialog(this, {
            buttons: [
                {
                    classes: 'btn-primary',
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_stop_recurrence',
                            args: [recurringResIds],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords(resIds);
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
                            args: [recurringResIds],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords(resIds);
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
                text: warning,
            }),
        }).open();
    }
});

export const ProjectListView = ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller: ProjectListController,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_list', ProjectListView);
