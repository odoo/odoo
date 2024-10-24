/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.notification.data) {
        const { action, model, res_id, type } = event.notification.data;
        if (model === "discuss.channel") {
            let route = `/odoo/${res_id}/action-${action}`;
            if (type === "call") {
                switch (event.action) {
                    case "accept":
                        route += "?call=accept";
                        break;
                    case "decline":
                        event.waitUntil(
                            fetch("/mail/rtc/channel/leave_call", {
                                headers: {
                                    "Content-type": "application/json",
                                },
                                body: JSON.stringify({
                                    id: 1,
                                    jsonrpc: "2.0",
                                    method: "call",
                                    params: {
                                        channel_id: res_id,
                                    },
                                }),
                                method: "POST",
                                mode: "cors",
                                credentials: "include",
                            })
                        );
                        return;
                }
            }
            event.waitUntil(clients.openWindow(route));
        } else {
            const modelPath = model.includes(".") ? model : `m-${model}`;
            event.waitUntil(clients.openWindow(`/odoo/${modelPath}/${res_id}`));
        }
    }
});
self.addEventListener("push", async (event) => {
    const notification = event.data.json();
    if (notification.options?.type === "cancel") {
        const notifications = await self.registration.getNotifications({
            tag: notification.options?.tag,
        });
        for (const notification of notifications) {
            notification.close();
        }
        return;
    }
    event.waitUntil(
        self.registration.showNotification(notification.title, notification.options || {})
    );
});
self.addEventListener("pushsubscriptionchange", async (event) => {
    const subscription = await self.registration.pushManager.subscribe(
        event.oldSubscription.options
    );
    await fetch("/web/dataset/call_kw/mail.push.device/register_devices", {
        headers: {
            "Content-type": "application/json",
        },
        body: JSON.stringify({
            id: 1,
            jsonrpc: "2.0",
            method: "call",
            params: {
                model: "mail.push.device",
                method: "register_devices",
                args: [],
                kwargs: {
                    ...subscription.toJSON(),
                    previousEndpoint: event.oldSubscription.endpoint,
                },
                context: {},
            },
        }),
        method: "POST",
        mode: "cors",
        credentials: "include",
    });
});
