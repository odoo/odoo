/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';
import { link } from '@mail/model/model_field_command';

function factory(dependencies) {

    class NotificationGroupManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        computeGroups() {
            // not supported for guests
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            for (const group of this.groups) {
                group.delete();
            }
            const groups = [];
            // TODO batch insert, better logic task-2258605
            this.messaging.currentPartner.failureNotifications.forEach(notification => {
                const thread = notification.message.originThread;
                // Notifications are grouped by model and notification_type.
                // Except for channel where they are also grouped by id because
                // we want to open the actual channel in discuss or chat window
                // and not its kanban/list/form view.
                const channelId = thread.model === 'mail.channel' ? thread.id : null;
                const id = `${thread.model}/${channelId}/${notification.notification_type}`;
                const group = this.messaging.models['mail.notification_group'].insert({
                    id,
                    notification_type: notification.notification_type,
                    res_model: thread.model,
                    res_model_name: thread.model_name,
                });
                group.update({ notifications: link(notification) });
                // avoid linking the same group twice when adding a notification
                // to an existing group
                if (!groups.includes(group)) {
                    groups.push(group);
                }
            });
            this.update({ groups: link(groups) });
        }

    }

    NotificationGroupManager.fields = {
        groups: one2many('mail.notification_group'),
    };
    NotificationGroupManager.identifyingFields = ['messaging'];
    NotificationGroupManager.modelName = 'mail.notification_group_manager';

    return NotificationGroupManager;
}

registerNewModel('mail.notification_group_manager', factory);
