/** @odoo-module **/

// ensure component is registered beforehand.
import '@mail/components/notification_alert/notification_alert';
import { getMessagingComponent } from "@mail/utils/messaging_component";

import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import Widget from 'web.Widget';
import widgetRegistry from 'web.widget_registry';

class NotificationAlertWrapper extends ComponentWrapper {}

// -----------------------------------------------------------------------------
// Display Notification alert on user preferences form view
// -----------------------------------------------------------------------------
const NotificationAlertWidget = Widget.extend(WidgetAdapterMixin, {
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
            getMessagingComponent("NotificationAlert"),
            {}
        );
        await this.component.mount(this.el);
    },
});

widgetRegistry.add('notification_alert', NotificationAlertWidget);

export default NotificationAlertWidget;
