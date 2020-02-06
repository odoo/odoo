odoo.define('mail_bot.messaging.widget.NotificationAlert', function (require) {
"use strict";

const components = {
    NotificationAlert: require('mail_bot.messaging.component.NotificationAlert'),
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
        this._super(...arguments);
        const env = this.call('messaging', 'getEnv');

        NotificationAlertWrapper.env = env;
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
