odoo.define('mail/static/src/models/notification_group_manager/notification_group_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class NotificationGroupManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        computeGroups() {
            for (const group of this.groups) {
                group.delete();
            }
            const groups = [];
            // TODO batch insert, better logic task-2258605
            this.env.messaging.currentPartner.failureNotifications.forEach(notification => {
                const thread = notification.message.originThread;
                // Notifications are grouped by model and notification_type.
                // Except for channel where they are also grouped by id because
                // we want to open the actual channel in discuss or chat window
                // and not its kanban/list/form view.
                const channelId = thread.model === 'mail.channel' ? thread.id : null;
                const id = `${thread.model}/${channelId}/${notification.notification_type}`;
                const group = this.env.models['mail.notification_group'].insert({
                    id,
                    notification_type: notification.notification_type,
                    res_model: thread.model,
                    res_model_name: thread.model_name,
                });
                group.update({ notifications: [['link', notification]] });
                // keep res_id only if all notifications are for the same record
                // set null if multiple records are present in the group
                let res_id = group.res_id;
                if (group.res_id === undefined) {
                    res_id = thread.id;
                } else if (group.res_id !== thread.id) {
                    res_id = null;
                }
                // keep only the most recent date from all notification messages
                let date = group.date;
                if (!date) {
                    date = notification.message.date;
                } else {
                    date = moment.max(group.date, notification.message.date);
                }
                group.update({
                    date,
                    res_id,
                });
                // avoid linking the same group twice when adding a notification
                // to an existing group
                if (!groups.includes(group)) {
                    groups.push(group);
                }
            });
            this.update({ groups: [['link', groups]] });
        }

    }

    NotificationGroupManager.fields = {
        groups: one2many('mail.notification_group'),
    };

    NotificationGroupManager.modelName = 'mail.notification_group_manager';

    return NotificationGroupManager;
}

registerNewModel('mail.notification_group_manager', factory);

});
