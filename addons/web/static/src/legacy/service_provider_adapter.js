/** @odoo-module **/

import { useService } from "@web/services/service_hook";
import { patch } from "@web/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { useListener } from "web.custom_hooks";
import { bus } from "web.core";

patch(WebClient.prototype, "web.service_provider_adapter", {
  setup() {
    // Effect Service
    const effect = useService("effect");
    useListener("show-effect", (ev) => {
      effect.create(ev.detail.message, ev.detail);
    });
    bus.on("show-effect", this, (payload) => {
      effect.create(payload.message, payload);
    });

    // Event call-service
    const notification = useService('notification');
    useListener('call-service', ev => {
        const payload = ev.detail;
        // Notification service
        if (payload.service === "notification") {
            if (payload.method === "notify") {
                let args = payload.args[0];
                let title = args.title;
                let message = args.message;
                if (args.subtitle) {
                    title = [title, args.subtitle].filter(Boolean).join(' ');
                }
                if (!message && title) {
                    message = title;
                    title = undefined;
                }
                const buttons = [];
                for (const button in args.buttons) {
                    buttons.push({
                        name: button.text,
                        icon: button.icon,
                        primary: button.primary,
                        onClick: button.click,
                    });
                }
                const notifId = notification.create(
                    message,
                    {
                        sticky: args.sticky,
                        title: title,
                        type: args.type,
                        className: args.className,
                        onClose: args.onClose,
                        buttons: buttons,
                    }
                );
                payload.callback(notifId);

            } else if (payload.method === "close") {
                //the legacy close method had 3 arguments : the notification id, silent and wait.
                //the new close method only has 2 arguments : the notification id and wait.
                notification.close(payload.args[0], payload.args[2] ? payload.args[2] : 0);
            }
        }

    });

    this._super(...arguments);
  },
});
