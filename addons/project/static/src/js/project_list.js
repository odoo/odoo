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

    _countRecordsPerReccurence(recurrenceIds, resIds) {
        return this._rpc({
            model: 'project.task',
            method: 'read_group',
            args: [
                [['recurrence_id', 'in', recurrenceIds], ['id', 'not in', resIds]],
                ['recurrence_id'],
                ['recurrence_id'],
            ],
        });
    },

    async _stopRecurrence(recurringResIds, resIds, mode) {
        const recurrenceIdsSet = new Set();
        for (const record of this.getSelectedRecords()) {
            const recurrenceId = record.data.recurrence_id;
            if (recurrenceId) {
                recurrenceIdsSet.add(recurrenceId);
            }
        }
        const recurrenceIds = Array.from(recurrenceIdsSet);
        // list recurrences that have tasks left after deleting/archiving
        let countsLeft = await this._countRecordsPerReccurence(recurrenceIds, recurringResIds);
        countsLeft = countsLeft.map(rec => rec.recurrence_id[0]);
        // so we check that no recurrence is absent, as it would mean no task is left
        const allowContinue = recurrenceIds.every(rec => countsLeft.includes(rec));

        let warning;
        if (resIds.length > 1) {
            warning = allowContinue
                    ? _t('It seems that some tasks are part of a recurrence.')
                    : _t('It seems that some tasks are part of a recurrence. At least one of them must be kept as a model to create the next occurences.');
        } else {
            warning = allowContinue
                    ? _t('It seems that this task is part of a recurrence.')
                    : _t('It seems that this task is part of a recurrence. You must keep it as a model to create the next occurences.');
        }

        const dialog = new Dialog(this, {
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
        });

        if (allowContinue) {
            Dialog.buttons.splice(1, 0,
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
            });
        }

        dialog.open();
    }
});

export const ProjectListView = ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller: ProjectListController,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_list', ProjectListView);
