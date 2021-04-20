self.addEventListener('install', function (ev) {
    console.log('service worker install');
    // ev.waitUntil(self.skipWaiting()); // Activate worker immediately
});

self.addEventListener('activate', function (ev) {
    console.log('service worker activate');
    // ev.waitUntil(self.clients.claim()); // Become available to all pages
});

let requestInProgress;

/**
 * @param {Request} request
 */
async function handleRequestLongpollingPoll(request) {
    console.log('catching /longpolling/poll');
    // const url = new self.URL(request.url);
    const body = await request.json();
    const last_bus_message_id = body.params.last_bus_message_id;
    if (!requestInProgress) {
        console.log('executing /longpolling/poll');
        requestInProgress = self.fetch('/longpolling/poll', {
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
            // signal: this._abortController.signal,
        }).then(response => {
            requestInProgress = undefined;
            // const response2 = response.clone();
            // if (response2 && response2.ok) {
            //     const data = await response2.json();
            // }
            return response;
        });
    }
    const response = await requestInProgress;
    console.log('responding /longpolling/poll');
    return response.clone();
}

self.addEventListener('fetch', (event) => {
    event.respondWith((() => {
        const url = new self.URL(event.request.url);
        if (url.pathname === '/longpolling/poll') {
            return handleRequestLongpollingPoll(event.request);
        }
        return self.fetch(event.request);
    })());
});
