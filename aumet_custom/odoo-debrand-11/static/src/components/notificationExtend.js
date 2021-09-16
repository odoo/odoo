
// Move to its own file in master.
odoo.define('odoo-debrand-11.notificationExtend', async function (require) {

const NotificationRequest = require('mail/static/src/components/notification_request/notification_request.js');
const { useBackButton } = require('web_mobile.hooks');

NotificationRequest.patch('odoo-debrand-11.notificationExtend', T =>
    class NotificationRequestPatch extends T {

    _handleResponseNotificationPermission(value) {
        // manually force recompute because the permission is not in the store
        this.env.messaging.messagingMenu.update();
        if (value !== 'granted') {alert("D");
            this.env.services['bus_service'].sendNotification(
                this.env._t("Permission denied"),
                this.env._t("Odooeeeeeee will not have the permission to send native notifications on this device.")
            );
        }
    }

    }

);
});
