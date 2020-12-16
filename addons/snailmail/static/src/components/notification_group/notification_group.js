odoo.define('snailmail/static/src/components/notification_group/notification_group.js', function (require) {
'use strict';

const components = {
    NotificationGroup: require('mail/static/src/components/notification_group/notification_group.js'),
};

const { patch } = require('web.utils');

patch(components.NotificationGroup, 'snailmail/static/src/components/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image() {
        if (this.group.notification_type === 'snail') {
            return '/snailmail/static/img/snailmail_failure.png';
        }
        return this._super(...arguments);
    },
});

});
