odoo.define('mail_bot/static/src/components/notification_list/notification_list.js', function (require) {
'use strict';

const components = {
    mail: {
        NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
    },
    mail_bot: {
        NotificationRequest: require('mail_bot/static/src/components/notification_request/notification_request.js'),
    },
};

const { patch } = require('web.utils');

Object.assign(components.mail.NotificationList.components, components.mail_bot);

patch(components.mail.NotificationList, 'mail_bot/static/src/components/notification_list/notification_list.js', {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override so that 'OdooBot has a request' is included at the top of the
     * list.
     *
     * @override
     */
    _useStoreSelector(props) {
        const res = this._super(...arguments);
        if (
            props.filter === 'all' &&
            this.env.messaging.isNotificationPermissionDefault()
        ) {
            res.notifications.unshift({
                type: 'odoobotRequest',
                uniqueId: `odoobotRequest`,
            });
        }
        return res;
    }
});

});
