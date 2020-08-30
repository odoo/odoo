odoo.define('mail/static/src/widgets/notification_alert/notification_alert.js', function (require) {
"use strict";

const components = {
    NotificationAlert: require('mail/static/src/components/notification_alert/notification_alert.js'),
};

const { ComponentWrapper, WidgetAdapterMixin } = require('web.OwlCompatibility');

const Widget = require('web.Widget');
const widgetRegistry = require('web.widget_registry');

class NotificationAlertWrapper extends ComponentWrapper {}

// -----------------------------------------------------------------------------
// Display Notification alert on user preferences form view
// -----------------------------------------------------------------------------
const NotificationAlert = Widget.extend(WidgetAdapterMixin, {
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.component = undefined;
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        this.component = new NotificationAlertWrapper(
            this,
            components.NotificationAlert,
            {}
        );
        await this.component.mount(this.el);
    },
});

widgetRegistry.add('notification_alert', NotificationAlert);

return NotificationAlert;

});
