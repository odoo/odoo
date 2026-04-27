/** @odoo-module ignore **/

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging.js";

window.firebase = {
    initializeApp,
    getMessaging,
    getToken,
    onMessage
};
