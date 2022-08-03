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

    async addressRecurrence(tasks, mode, callback = () => {}) {
        const recurrentTaskIds = [];
        let hasRecurrentTasks = false;
        for (const task of tasks) {
            if (task.data.recurrence_id) {
                recurrentTaskIds.push(task.resId);
                hasRecurrentTasks = true;
            }
        }
        if (!hasRecurrentTasks) {
            callback();
            return;
        }

        const dialogProps = {
            body: '',
            confirm: () => {},
            cancel: () => {},
            addressRecurrence: async (target) => {
                await this.orm.call(
                    this.resModel,
                    'action_address_recurrence',
                    [recurrentTaskIds, target, mode],
                );
                callback();
            },
            mode: mode,
        };
        this.dialog.add(ProjectStopRecurrenceConfirmationDialog, dialogProps);
    }
}

export const taskRecurrenceService = {
    dependencies: ['dialog', 'orm'],
    async: [
        'addressRecurrence',
    ],
    start(env, { dialog, orm }) {
        return new ProjectTaskRecurrence(env, dialog, orm);
    }
};

registry.category('services').add('project_task_recurrence', taskRecurrenceService);
