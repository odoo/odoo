/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.notification.data) {
        const { action, model, res_id } = event.notification.data;
        if (model === "discuss.channel") {
            clients.openWindow(`/web#action=${action}&active_id=${res_id}`);
        } else {
            clients.openWindow(`/web#model=${model}&id=${res_id}`);
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
    await fetch("/web/dataset/call_kw/mail.partner.device/register_devices", {
        headers: {
            "Content-type": "application/json",
        },
        body: JSON.stringify({
            id: 1,
            jsonrpc: "2.0",
            method: "call",
            params: {
                model: "mail.partner.device",
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
