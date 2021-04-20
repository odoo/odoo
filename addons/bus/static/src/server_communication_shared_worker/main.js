self.addEventListener('install', function (ev) {
    console.log('service worker install');
    // ev.waitUntil(self.skipWaiting()); // Activate worker immediately
});

self.addEventListener('activate', function (ev) {
    console.log('service worker activate');
    // ev.waitUntil(self.clients.claim()); // Become available to all pages
});

let longpollingPollRequestPromise;
let longpollingPollAbortController;

/**
 * @param {Request} request
 */
async function handleRequestWebLogin(request) {
    if (request.method === 'POST' && longpollingPollAbortController) {
        // Cancel pending requests to prevent "session expired" after login
        // which would happen if the server finished processing a pending
        // request as guest after the login.
        // TODO maybe also do on logout, and all other ways to change session?
        longpollingPollAbortController.abort();
    }
    return self.fetch(request);
}

/**
 * @param {Request} request
 */
async function handleRequestLongpollingPoll(request) {
    // const url = new self.URL(request.url);
    const body = await request.json();
    const last_bus_message_id = body.params.last_bus_message_id;
    if (!longpollingPollRequestPromise) {
        longpollingPollAbortController = new self.AbortController();
        longpollingPollRequestPromise = self.fetch('/longpolling/poll', {
            body: JSON.stringify({
                id: Math.floor(Math.random() * 1000 * 1000 * 1000),
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    // TODO SEB handle new channels (only for livechat?)
                    channels: [],
                    last_bus_message_id: last_bus_message_id,
                },
            }),
            headers: {
                'Content-Type': 'application/json',
            },
            method: 'POST',
            signal: longpollingPollAbortController.signal,
        }).then(response => {
            // const response2 = response.clone();
            // if (response2 && response2.ok) {
            //     const data = await response2.json();
            // }
            return response;
        }).finally(() => {
            longpollingPollRequestPromise = undefined;
            longpollingPollAbortController = undefined;
        });
    }
    const response = await longpollingPollRequestPromise;
    // TODO for correct implementation of jsonrpc, this should return the same
    // "id" as the one that was used for each request (from each tab)
    return response.clone();
}

self.addEventListener('fetch', (event) => {
    event.respondWith((() => {
        const url = new self.URL(event.request.url);
        switch (url.pathname) {
            case '/web/login': {
                return handleRequestWebLogin(event.request);
            }
            case '/longpolling/poll': {
                return handleRequestLongpollingPoll(event.request);
            }
        }
        return self.fetch(event.request);
    })());
});
