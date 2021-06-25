odoo.define('sms/static/src/components/notification_group/notification_group.js', function (require) {
'use strict';

const { NotificationGroup } = require('@mail/components/notification_group/notification_group');

const { patch } = require('web.utils');

const components = { NotificationGroup };

patch(components.NotificationGroup.prototype, 'sms/static/src/components/notification_group/notification_group.js', {

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
