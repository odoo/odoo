/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'NotificationGroup',
    recordMethods: {
        /**
         * @override
         */
        _openDocuments() {
            if (this.notification_type !== 'sms') {
                return this._super(...arguments);
            }
            this.env.services.action.doAction({
                name: this.env._t("SMS Failures"),
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: this.res_model,
                domain: [['message_has_sms_error', '=', true]],
                context: { create: false },
            });
            if (this.messaging.device.isSmall) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.messaging.messagingMenu.close();
            }
        },
    },
});
