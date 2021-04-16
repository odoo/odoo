odoo.define('web.public.Notification', function (require) {
'use strict';

var Notification = require('web.Notification');

Notification.include({
    xmlDependencies: ['/web/static/src/legacy/frontend/notification/notification.xml'],
});
});
