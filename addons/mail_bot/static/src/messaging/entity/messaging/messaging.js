odoo.define('mail_bot.messaging.entity.Messaging', function (require) {
'use strict';

const { registerClassPatchEntity } = require('mail.messaging.entity.core');

registerClassPatchEntity('Messaging', 'mail_bot.messaging.entity.Messaging', {
    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    isNotificationPermissionDefault() {
        const windowNotification = this.env.window.Notification;
        return windowNotification
            ? windowNotification.permission === 'default'
            : false;
    },
});

});
