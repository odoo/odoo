/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */

const PUSH_NOTIFICATION_TYPE = {
    CALL: "CALL",
    CANCEL: "CANCEL",
};
const PUSH_NOTIFICATION_ACTION = {
    ACCEPT: "ACCEPT",
    DECLINE: "DECLINE",
};

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.notification.data) {
        const { action, model, res_id, type } = event.notification.data;
        if (model === "discuss.channel") {
            const route = `/odoo/${res_id}/action-${action}`;
            if (type === PUSH_NOTIFICATION_TYPE.CALL) {
                switch (event.action) {
                    case PUSH_NOTIFICATION_ACTION.ACCEPT: {
                        event.waitUntil(
                            (async () => {
                                const clientWindows = await clients.matchAll({
                                    includeUncontrolled: true,
                                    type: "window",
                                });
                                const clientWindow = clientWindows[0];
                                if (clientWindow) {
                                    clientWindow.focus();
                                    clientWindow.postMessage({
                                        action: "JOIN_CALL",
                                        id: res_id,
                                    });
                                    return;
                                }
                                await clients.openWindow(route + "?call=accept");
                            })()
                        );
                        return;
                    }
                    case PUSH_NOTIFICATION_ACTION.DECLINE:
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
    switch (notification.options?.data?.type) {
        case PUSH_NOTIFICATION_TYPE.CALL:
            if (notification.options.actions && navigator.userAgent.includes("Android")) {
                // action "accept" is disabled on mobile until: https://issues.chromium.org/issues/40286493 is fixed.
                delete notification.options.actions.accept;
            }
            break;
        case PUSH_NOTIFICATION_TYPE.CANCEL: {
            const notifications = await self.registration.getNotifications({
                tag: notification.options?.tag,
            });
            for (const notification of notifications) {
                notification.close();
            }
            return;
        }
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
