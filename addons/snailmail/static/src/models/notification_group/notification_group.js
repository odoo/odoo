/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/notification_group/notification_group';

patchRecordMethods('NotificationGroup', {
    /**
     * @override
     */
    openCancelAction() {
        if (this.notification_type !== 'snail') {
            return this._super(...arguments);
        }
        this.env.bus.trigger('do-action', {
            action: 'snailmail.snailmail_letter_cancel_action',
            options: {
                additional_context: {
                    default_model: this.res_model,
                    unread_counter: this.notifications.length,
                },
            },
        });
    },
    /**
     * @override
     */
    _openDocuments() {
        if (this.notification_type !== 'snail') {
            return this._super(...arguments);
        }
        this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Snailmail Failures"),
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: this.res_model,
                domain: [['message_ids.snailmail_error', '=', true]],
            },
        });
        if (this.messaging.device.isMobile) {
            // messaging menu has a higher z-index than views so it must
            // be closed to ensure the visibility of the view
            this.messaging.messagingMenu.close();
        }
    },
});
