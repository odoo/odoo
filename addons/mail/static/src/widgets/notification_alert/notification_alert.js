/** @odoo-module **/

import NotificationAlertComponent from '@mail/components/notification_alert/notification_alert';

import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import Widget from 'web.Widget';
import widgetRegistry from 'web.widget_registry';

const components = { NotificationAlertComponent };

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
            components.NotificationAlertComponent,
            {}
        );
        await this.component.mount(this.el);
    },
});

widgetRegistry.add('notification_alert', NotificationAlert);

export default NotificationAlert;
