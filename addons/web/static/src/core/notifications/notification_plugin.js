import { Plugin, Resource, types as t, untrack, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { registry } from "@web/core/registry";

const AUTOCLOSE_DELAY = 4000;

const NotificationOptionSchema = t.object({
    type: t.selection(["warning", "danger", "success", "info"]).optional("warning"),
    title: t.or([t.string(), t.boolean(), t.object({ toString: t.function() })]).optional(),
    className: t.string().optional(""),
    buttons: t.array(
        t.object({
            name: t.string(),
            icon: t.string().optional(),
            primary: t.boolean().optional(),
            onClick: t.function(),
        })
    ).optional([]),
    sticky: t.boolean().optional(),
    autocloseDelay: t.number().optional(AUTOCLOSE_DELAY),
    close: t.function(),
});

export const NotificationSchema = t.and([
    t.object({
        message: t.customValidator(
            t.any(),
            (m) =>
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
        ),
    }),
    NotificationOptionSchema,
]);

const NotificationOptionWrapperSchema = t.object({
    id: t.number(),
    props: NotificationSchema,
    onClose: t.function().optional(),
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
     * @param {Translation} message
     * @param {NotificationOptionSchema} [options]
     */
    add(message, options = {}) {
        return untrack(() => {
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
        });
    }

    /**
     * @private
     * @param {NotificationOptionWrapperSchema} notification
     */
    close(notification) {
        untrack(() => {
            if (this.notifications.has(notification)) {
                if (notification.onClose) {
                    notification.onClose();
                }
                this.notifications.delete(notification);
            }
        });
    }
}

services.add(NotificationPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the notification service are removed
 * -----------------------------------------------------------------------------
 */
export const notificationService = {
    start() {
        return usePlugin(NotificationPlugin);
    },
};

registry.category("services").add("notification", notificationService);
