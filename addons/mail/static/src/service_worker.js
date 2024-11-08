/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    async function handleNavigation(url) {
        const windowClients = await clients.matchAll({
            type: "window",
            includeUncontrolled: true,
        });
        const odooClient = windowClients.find(
            (client) => client.url && client.url.includes("/odoo")
        );
        if (odooClient) {
            await odooClient.focus();
            await odooClient.navigate(url);
        } else {
            clients.openWindow(url);
        }
    }

    if (event.notification.data) {
        const { action, model, res_id } = event.notification.data;
        const url =
            model === "discuss.channel"
                ? `/odoo/${res_id}/action-${action}`
                : `/odoo/${model.includes(".") ? model : `m-${model}`}/${res_id}`;
        event.waitUntil(handleNavigation(url));
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
