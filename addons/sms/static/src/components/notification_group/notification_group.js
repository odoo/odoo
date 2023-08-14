odoo.define('sms/static/src/components/notification_group/notification_group.js', function (require) {
'use strict';

const components = {
    NotificationGroup: require('mail/static/src/components/notification_group/notification_group.js'),
};

const { patch } = require('web.utils');

patch(components.NotificationGroup, 'sms/static/src/components/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image() {
        if (this.group.notification_type === 'sms') {
            return '/sms/static/img/sms_failure.svg';
        }
        return this._super(...arguments);
    },
});

});
