/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
const MAX_FETCH_CACHE_SIZE = 20;
const channelFetchedResponseByMessageId = new Map();

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
self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    if (url.pathname === "/discuss/channel/mark_as_fetched") {
        event.respondWith(
            (async () => {
                try {
                    const request = event.request.clone();
                    const payload = await request.json();
                    const { last_message_id } = payload.params;
                    if (channelFetchedResponseByMessageId.has(last_message_id)) {
                        return channelFetchedResponseByMessageId
                            .get(last_message_id)
                            .then((resp) => resp.clone());
                    }
                    if (channelFetchedResponseByMessageId.size >= MAX_FETCH_CACHE_SIZE) {
                        const firstKey = channelFetchedResponseByMessageId.keys().next().value;
                        channelFetchedResponseByMessageId.delete(firstKey);
                    }
                    const fetch_promise = fetch(event.request);
                    channelFetchedResponseByMessageId.set(last_message_id, fetch_promise);
                    const response = await fetch_promise;
                    const responseBody = await response.clone().json();
                    if (response.status >= 400 || "error" in responseBody) {
                        channelFetchedResponseByMessageId.delete(last_message_id);
                    }
                    return response;
                } catch {
                    return fetch(event.request);
                }
            })()
        );
    }
});
