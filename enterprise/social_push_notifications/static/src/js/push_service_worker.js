/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
/* global firebase */

importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");

const getFirebaseConfig = () => {
    const params = new URLSearchParams(self.location.search);
    return {
        appId: params.get("appId"),
        apiKey: params.get("apiKey"),
        projectId: params.get("projectId"),
        messagingSenderId: params.get("messagingSenderId"),
    };
};

// Initialize the Firebase app in the service worker by passing the config in the URL.
firebase.initializeApp(getFirebaseConfig());
firebase.messaging();
