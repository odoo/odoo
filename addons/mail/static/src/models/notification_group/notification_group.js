/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert, unlink } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'NotificationGroup',
    identifyingFields: ['res_model', 'res_id', 'notification_type'],
    recordMethods: {
        /**
         * Opens the view that allows to cancel all notifications of the group.
         */
        openCancelAction() {
            if (this.notification_type !== 'email') {
                return;
            }
            this.env.bus.trigger('do-action', {
                action: 'mail.mail_resend_cancel_action',
                options: {
                    additional_context: {
                        default_model: this.res_model,
                        unread_counter: this.notifications.length,
                    },
                },
            });
        },
        /**
         * Opens the view that displays either the single record of the group or
         * all the records in the group.
         */
        openDocuments() {
            if (this.thread) {
                this.thread.open();
            } else {
                this._openDocuments();
            }
        },
        /**
         * @private
         * @returns {Thread|undefined}
         */
        _computeThread() {
            const notificationsThreadIds = this.notifications
                  .filter(notification => notification.message && notification.message.originThread)
                  .map(notification => notification.message.originThread.id);
            const threadIds = new Set(notificationsThreadIds);
            if (threadIds.size !== 1) {
                return unlink();
            }
            return insert({
                id: notificationsThreadIds[0],
                model: this.res_model,
            });
        },
        /**
         * Compute the most recent date inside the notification messages.
         *
         * @private
         * @returns {moment|undefined}
         */
        _computeDate() {
            const dates = this.notifications
                  .filter(notification => notification.message && notification.message.date)
                  .map(notification => notification.message.date);
            if (dates.length === 0) {
                return clear();
            }
            return moment.max(dates);
        },
        /**
         * Compute the position of the group inside the notification list.
         *
         * @private
         * @returns {number}
         */
        _computeSequence() {
            return -Math.max(...this.notifications.map(notification => notification.message.id));
        },
        /**
         * @private
         */
        _onChangeNotifications() {
            if (this.notifications.length === 0) {
                this.delete();
            }
        },
        /**
         * Opens the view that displays all the records of the group.
         *
         * @private
         */
        _openDocuments() {
            if (this.notification_type !== 'email') {
                return;
            }
            this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("Mail Failures"),
                    type: 'ir.actions.act_window',
                    view_mode: 'kanban,list,form',
                    views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                    target: 'current',
                    res_model: this.res_model,
                    domain: [['message_has_error', '=', true]],
                    context: { create: false },
                },
            });
            if (this.messaging.device.isMobile) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.messaging.messagingMenu.close();
            }
        },
    },
    fields: {
        /**
         * States the most recent date of all the notification message.
         */
        date: attr({
            compute: '_computeDate',
        }),
        notification_type: attr({
            readonly: true,
        }),
        notifications: many('Notification', {
            inverse: 'notificationGroup',
        }),
        notificationGroupViews: many('NotificationGroupView', {
            inverse: 'notificationGroup',
            isCausal: true,
        }),
        res_id: attr({
            readonly: true,
        }),
        res_model: attr({
            readonly: true,
        }),
        res_model_name: attr(),
        /**
         * States the position of the group inside the notification list.
         */
        sequence: attr({
            compute: '_computeSequence',
            default: 0,
        }),
        /**
         * Related thread when the notification group concerns a single thread.
         */
        thread: one('Thread', {
            compute: '_computeThread',
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['notifications'],
            methodName: '_onChangeNotifications',
        }),
    ],
});
