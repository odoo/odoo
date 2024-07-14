/* global firebase */
/* eslint-env serviceworker */
// Give the service worker access to Firebase Messaging.
importScripts('https://www.gstatic.com/firebasejs/6.3.4/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/6.3.4/firebase-messaging.js');

// firebase code expects a 'self' variable to be defined
// didn't find any explanation for this on the web, everyone seems cool with it
var self = this;

var senderId = this.location.search.replace('?senderId=', '');
// Initialize the Firebase app in the service worker by passing in the messagingSenderId
firebase.initializeApp({
    'messagingSenderId': senderId
});

// Add an event listener to handle notification clicks
self.addEventListener('notificationclick', function (event) {
    if (event.action === 'close') {
        event.notification.close();
    } else if (event.notification.data.target_url && '' !== event.notification.data.target_url.trim()) {
        // user clicked on the notification itself or on the 'open' action
        // clients is a reserved variable in the service worker context.
        // check https://developer.mozilla.org/en-US/docs/Web/API/Clients/openWindow

        clients.openWindow(event.notification.data.target_url);
    }
});

// Retrieve an instance of Firebase Messaging so that it can handle background messages
// This line HAS to stay after the event listener or it will break it
// https://stackoverflow.com/questions/50869015/firefox-not-opening-window-in-service-worker-for-push-message
const messaging = firebase.messaging();

messaging.setBackgroundMessageHandler(function (payload) {
    var notificationData = payload.data;

    return self.registration.showNotification(notificationData.title, {
        body: notificationData.body,
        icon: notificationData.icon,
        data: {
            target_url: notificationData.target_url,
        }
    });
});
