import { plugin, Plugin, Resource, types as t } from "@odoo/owl";
import { services } from "@web/core/services";
import { registry } from "@web/core/registry";

export const NotificationOptionSchema = t.object({
    "type?": t.selection(["warning", "danger", "success", "info"]),
    "title?": t.or([t.string(), t.boolean(), t.object({ toString: t.function() })]),
    "className?": t.string(),
    "buttons?": t.array(
        t.object({
            name: t.string(),
            "icon?": t.string(),
            "primary?": t.boolean(),
            onClick: t.function(),
        })
    ),
    "sticky?": t.boolean(),
    "autocloseDelay?": t.number(),
    close: t.function(),
});

export const NotificationSchema = t.and([
    t.object({
        message: t.or([t.string(), t.object({ toString: t.function() })]),
    }),
    NotificationOptionSchema,
]);

export const NotificationOptionWrapperSchema = t.object({
    id: t.number(),
    props: NotificationSchema,
    "onClose?": t.function(),
});

export class NotificationPlugin extends Plugin {
    /** @private */
    notifId = 0;
    /** @private */
    notifications = new Resource({
        name: "notifications",
        validation: NotificationOptionWrapperSchema,
    });

    /**
     * @param {string} message
     * @param {NotificationOptionSchema} [options]
     */
    add(message, options = {}) {
        const id = ++this.notifId;
        const closeFn = () => this.close(notification);
        const props = Object.assign({}, options, { message, close: closeFn });
        delete props.onClose;
        const notification = { id, props, onClose: options.onClose };
        for (const notif of this.notifications.items()) {
            if (notif.props.message.toString() === notification.props.message.toString()) {
                this.close(notif);
            }
        }
        this.notifications.add(notification);
        return closeFn;
    }

    /**
     * @private
     * @param {NotificationOptionWrapperSchema} notification
     */
    close(notification) {
        if (this.notifications.has(notification)) {
            if (notification.onClose) {
                notification.onClose();
            }
            this.notifications.delete(notification);
        }
    }
}

services.add(NotificationPlugin);

// temporary - to remove when all uses of the notificationService
// are removed
registry.category("services").add("notification", {
    start() {
        return plugin(NotificationPlugin);
    },
});
