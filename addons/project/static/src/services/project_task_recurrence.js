/** @odoo-module */

import { registry } from "@web/core/registry";

import { ProjectStopRecurrenceConfirmationDialog } from '../components/project_stop_recurrence_confirmation_dialog/project_stop_recurrence_confirmation_dialog';

class ProjectTaskRecurrence {
    constructor(env, dialog, orm) {
        this.env = env;
        this.dialog = dialog;
        this.orm = orm;
        this.resModel = 'project.task';
    }

    async stopRecurrence(tasks, callback = () => {}) {
        const taskIdsWithRecurrence = [];
        const tasksPerRecurrence = {};
        const recurrenceIds = [];
        for (const task of tasks) {
            if (task.data.recurrence_id) {
                taskIdsWithRecurrence.push(task.resId);
                const recurrenceId = task.data.recurrence_id && task.data.recurrence_id[0];
                if (!(recurrenceId in tasksPerRecurrence)) {
                    tasksPerRecurrence[recurrenceId] = [task.resId];
                    recurrenceIds.push(recurrenceId);
                } else {
                    tasksPerRecurrence[recurrenceId].push(task.resId);
                }
            }
        }

        if (!recurrenceIds.length) {
            callback();
            return;
        }

        let allowContinue = false;
        if (recurrenceIds.length === 1) {
            const count = await this.orm.searchCount(
                this.resModel,
                [['recurrence_id', '=', recurrenceIds[0]]],
            );
            allowContinue = count != 1;
        } else {
            const taskReadGroup = await this.orm.readGroup(
                this.resModel,
                [['recurrence_id', 'in', recurrenceIds]],
                ['recurrence_id'],
                ['recurrence_id'],
            );
            allowContinue = true;
            for (const res of taskReadGroup) {
                const taskCount = tasksPerRecurrence[res.recurrence_id[0]].length;
                if (taskCount === res.recurrence_id_count) {
                    allowContinue = false;
                    break;
                }
            }
        }
        let dialogBody;
        if (tasks.length > 1) {
            dialogBody = allowContinue
                    ? this.env._t('It seems that some tasks are part of a recurrence.')
                    : this.env._t('It seems that some tasks are part of a recurrence. At least one of them must be kept as a model to create the next occurences.');
        } else {
            dialogBody = allowContinue
                    ? this.env._t('It seems that this task is part of a recurrence.')
                    : this.env._t('It seems that this task is recurrent. Would you like to stop its recurrence?');
        }

        const dialogProps = {
            body: dialogBody,
            confirm: async () => {
                await this.orm.call(
                    this.resModel,
                    'action_stop_recurrence',
                    [taskIdsWithRecurrence],
                );
                callback();
            },
            cancel: () => {},
        };
        if (allowContinue) {
            dialogProps.continueRecurrence = async () => {
                await this.orm.call(
                    this.resModel,
                    'action_continue_recurrence',
                    [taskIdsWithRecurrence],
                );
                callback();
            };
        }
        this.dialog.add(ProjectStopRecurrenceConfirmationDialog, dialogProps);
    }
}

export const taskRecurrenceService = {
    dependencies: ['dialog', 'orm'],
    async: [
        'stopRecurrence',
    ],
    start(env, { dialog, orm }) {
        return new ProjectTaskRecurrence(env, dialog, orm);
    }
};

registry.category('services').add('project_task_recurrence', taskRecurrenceService);
