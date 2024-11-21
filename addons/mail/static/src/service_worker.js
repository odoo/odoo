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
    self.registration.showNotification(notification.title, notification.options || {});
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
