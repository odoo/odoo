odoo.define('im_livechat/static/src/components/notification_list/notification_list.js', function (require) {
'use strict';

const components = {
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
};

components.NotificationList._allowedFilters.push('livechat');

});
