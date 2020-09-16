odoo.define('mail/static/src/models/notification_group_manager/notification_group_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2many } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class NotificationGroupManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        computeGroups() {
            for (const group of this.__mfield_groups(this)) {
                group.delete();
            }
            const groups = [];
            // TODO batch insert, better logic task-2258605
            this.env.messaging.__mfield_currentPartner(this).__mfield_failureNotifications(this).forEach(notification => {
                const thread = notification.__mfield_message(this).__mfield_originThread(this);
                // Notifications are grouped by model and notification_type.
                // Except for channel where they are also grouped by id because
                // we want to open the actual channel in discuss or chat window
                // and not its kanban/list/form view.
                const channelId = thread.__mfield_model(this) === 'mail.channel' ? thread.__mfield_id(this) : null;
                const id = `${thread.__mfield_model(this)}/${channelId}/${notification.__mfield_notification_type(this)}`;
                const group = this.env.models['mail.notification_group'].insert({
                    __mfield_id: id,
                    __mfield_notification_type: notification.__mfield_notification_type(this),
                    __mfield_res_model: thread.__mfield_model(this),
                    __mfield_res_model_name: thread.__mfield_model_name(this),
                });
                group.update({
                    __mfield_notifications: [['link', notification]],
                });
                // keep res_id only if all notifications are for the same record
                // set null if multiple records are present in the group
                let res_id = group.__mfield_res_id(this);
                if (group.__mfield_res_id(this) === undefined) {
                    res_id = thread.__mfield_id(this);
                } else if (group.__mfield_res_id(this) !== thread.__mfield_id(this)) {
                    res_id = null;
                }
                // keep only the most recent date from all notification messages
                let date = group.__mfield_date(this);
                if (!date) {
                    date = notification.__mfield_message(this).__mfield_date(this);
                } else {
                    date = moment.max(group.__mfield_date(this), notification.__mfield_message(this).__mfield_date(this));
                }
                group.update({
                    __mfield_date: date,
                    __mfield_res_id: res_id,
                });
                // avoid linking the same group twice when adding a notification
                // to an existing group
                if (!groups.includes(group)) {
                    groups.push(group);
                }
            });
            this.update({
                __mfield_groups: [['link', groups]],
            });
        }

    }

    NotificationGroupManager.fields = {
        __mfield_groups: one2many('mail.notification_group'),
    };

    NotificationGroupManager.modelName = 'mail.notification_group_manager';

    return NotificationGroupManager;
}

registerNewModel('mail.notification_group_manager', factory);

});
