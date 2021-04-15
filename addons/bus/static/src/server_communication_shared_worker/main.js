self.addEventListener('install', function (ev) {
    console.log('service worker install');
    // ev.waitUntil(self.skipWaiting()); // Activate worker immediately
});

self.addEventListener('activate', function (ev) {
    console.log('service worker activate');
    // ev.waitUntil(self.clients.claim()); // Become available to all pages
});

self.addEventListener('message', function (ev) {
    console.log('service worker message', ev.ports, ev.data);
    ev.source.postMessage("Hi client");
});
