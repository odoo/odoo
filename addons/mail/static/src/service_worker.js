/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */

async function openDiscussChannel(channelId, action) {
    const discussURLRegexes = [
        new RegExp("/odoo/discuss"),
        new RegExp(`/odoo/\\d+/action-${action}`),
        new RegExp(`/odoo/action-${action}`),
    ];
    let targetClient;
    for (const client of await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
    })) {
        if (!targetClient || discussURLRegexes.some((r) => r.test(new URL(client.url).pathname))) {
            targetClient = client;
        }
    }
    if (!targetClient) {
        targetClient = await self.clients.openWindow(
            `/odoo/action-${action}?active_id=discuss.channel_${channelId}`
        );
    }
    await targetClient.focus();
    targetClient.postMessage({ action: "OPEN_CHANNEL", data: { id: channelId } });
}

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.notification.data) {
        const { action, model, res_id } = event.notification.data;
        if (model === "discuss.channel") {
            event.waitUntil(openDiscussChannel(res_id, action));
        } else {
            const modelPath = model.includes(".") ? model : `m-${model}`;
            clients.openWindow(`/odoo/${modelPath}/${res_id}`);
        }
    }
});
self.addEventListener("push", (event) => {
    const notification = event.data.json();
    event.waitUntil(handlePushEvent(notification));
});

/** @type {Map<string, Function>} string is correlationId and Function is handler */
self.handlePushEventMessageFns = new Map();

self.addEventListener("message", ({ data }) => {
    const { type, payload } = data;
    if (type === "notification-display-response") {
        const fn = self.handlePushEventMessageFns.get(payload.correlationId);
        if (fn) {
            self.handlePushEventMessageFns.delete(payload.correlationId);
            fn({ data });
        }
    }
});

async function handlePushEvent(notification) {
    const { model, res_id } = notification.options?.data || {};
    const correlationId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    let timeoutId;
    let promResolve;
    const onHandlePushEventMessage = ({ data = {} }) => {
        const { type, payload } = data;
        if (type === "notification-display-response" && payload.correlationId === correlationId) {
            clearTimeout(timeoutId);
            promResolve?.();
        }
    };
    return new Promise((resolve) => {
        promResolve = resolve;
        self.handlePushEventMessageFns.set(correlationId, onHandlePushEventMessage);
        self.clients.matchAll({ includeUncontrolled: true, type: "window" }).then((clients) => {
            clients.forEach((client) =>
                client.postMessage({
                    type: "notification-display-request",
                    payload: { correlationId, model, res_id },
                })
            );
        });
        timeoutId = setTimeout(() => {
            resolve(self.registration.showNotification(notification.title, notification.options));
        }, 500);
    });
}
self.addEventListener("pushsubscriptionchange", async (event) => {
    if (!event.oldSubscription) {
        return;
    }
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
