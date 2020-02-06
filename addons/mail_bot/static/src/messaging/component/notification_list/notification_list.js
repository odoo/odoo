odoo.define('mail_bot.messaging.component.NotificationList', function (require) {
'use strict';

const components = {
    mail: {
        NotificationList: require('mail.messaging.component.NotificationList'),
    },
    mail_bot: {
        NotificationRequest: require('mail_bot.messaging.component.NotificationRequest'),
    },
};

const { patch } = require('web.utils');

Object.assign(components.mail.NotificationList.components, components.mail_bot);

patch(components.mail.NotificationList, 'mail_bot.messaging.component.NotificationList', {

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
            this.env.messaging.constructor.isNotificationPermissionDefault()
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
