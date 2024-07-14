/** @odoo-module **/
/* global firebase */

import publicWidget from "@web/legacy/js/public/public_widget";
import { browser } from "@web/core/browser/browser";
import NotificationRequestPopup from "@social_push_notifications/js/push_notification_request_popup";
import { Component } from "@odoo/owl";

publicWidget.registry.NotificationWidget =  publicWidget.Widget.extend({
    selector: '#wrapwrap',

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.notification = this.bindService("notification");
    },

    /**
     * This will start listening to notifications if permission was already granted
     * by the user or ask for permission after a timeout (configurable) and then start listening.
     *
     * @override
     */
    start: function () {
        var self = this;
        var superPromise = this._super.apply(this, arguments);

        if (!this._isBrowserCompatible()) {
            return superPromise;
        }

        if (Notification.permission === "granted") {
            const { pushConfigurationPromise, wasUpdated } = this._getNotificationRequestConfiguration();
            pushConfigurationPromise.then((pushConfiguration) => {
                if (Object.keys(pushConfiguration).length === 1) {
                    return superPromise;
                }
                const messaging = self._initializeFirebaseApp(pushConfiguration);
                if (wasUpdated) {
                    self._registerServiceWorker(pushConfiguration, messaging);
                }
                self._setForegroundNotificationHandler(pushConfiguration, messaging);
            });
        } else if (Notification.permission !== "denied") {
            this._askPermission();
        }
        Component.env.bus.addEventListener('open_notification_request', (ev) => this._onNotificationRequest(...ev.detail));

        return superPromise;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will handle Firebase Messaging foreground notifications.
     *
     * The push notifications will only be displayed is the user has
     * granted notification permission to the website.
     *
     * See: https://rnfirebase.io/messaging/usage#foreground-state-messages
     *
     * @private
     */
    _setForegroundNotificationHandler: function (config, messaging) {
        const onMessage = (payload) => {
            if (window.Notification && Notification.permission === "granted") {
                const notificationData = payload.data;
                const options = {
                    title: notificationData.title,
                    type: 'success',
                };
                const targetUrl = notificationData.target_url;
                if (targetUrl) {
                    options.buttons = [{
                        name: 'Open',
                        onClick: () => window.open(targetUrl, '_blank'),
                    }];
                }
                this.notification.add(notificationData.body, options);
            }
        };
        messaging = messaging || this._initializeFirebaseApp(config);
        if (!messaging) {
            return;
        }
        messaging.onMessage(onMessage);
    },

    /**
     * Will check browser compatibility before trying to register the service worker.
     * Browsers compatible now (11/07/2019):
     * - Chrome
     * - Firefox
     * - Edge
     *
     * For Safari we would need to use an entirely different service since they have their own
     * push notifications mechanism.
     * See: https://developer.apple.com/notifications/safari-push-notifications/
     *
     * @private
     */
    _isBrowserCompatible: function () {
        if (!('serviceWorker' in navigator)) {
            // Service Worker isn't supported on this browser
            return false;
        }

        if (!('PushManager' in window)) {
            // Push isn't supported on this browser
            return false;
        }

        return true;
    },

    /**
     * Will initialize the firebase app with the given configuration
     * and return the messaging object.
     *
     * @param {Object} config the push configuration
     * @returns {firebase.messaging.Messaging}
     *
     * @private
     */
    _initializeFirebaseApp: function (config) {
        if (!config.firebase_push_certificate_key
            || !config.firebase_project_id
            || !config.firebase_web_api_key) {
            // missing configuration
            return null;
        }

        firebase.initializeApp({
            apiKey: config.firebase_web_api_key,
            projectId: config.firebase_project_id,
            messagingSenderId: config.firebase_sender_id
        });

        var messaging = firebase.messaging();
        return messaging;
    },

    /**
     * Will register a service worker to display later notifications.
     * This method also handles the notification "subscription token".
     *
     * The token will be used by firebase to notify this user directly.
     *
     * @param {Object} config the push configuration
     * @param {firebase.messaging.Messaging} messaging
     *
     * @private
     */
    _registerServiceWorker: function (config, messaging) {
        const self = this;

        messaging = messaging || this._initializeFirebaseApp(config);
        if (!messaging) {
            return;
        }

        var baseWorkerUrl = '/social_push_notifications/static/src/js/push_service_worker.js';
        navigator.serviceWorker.register(baseWorkerUrl + '?senderId=' + encodeURIComponent(config.firebase_sender_id))
            .then(function (registration) {
                messaging.useServiceWorker(registration);
                messaging.usePublicVapidKey(config.firebase_push_certificate_key);
                messaging.getToken().then(function (token) {
                    self._registerToken(token);
                });
        });
    },

    /**
     * Checks that the push notification configuration is still up to date.
     * (It expires after 7 days)
     *
     * @private
     */
    _isConfigurationUpToDate: function (pushConfiguration) {
        if (pushConfiguration) {
            if (new Date() < new Date(pushConfiguration.expirationDate)) {
                return true;
            }
        }

        return false;
    },

    /**
     * Responsible for fetching the full push configuration.
     *
     * When the configuration is fetched, it's stored into local storage (for 7 days)
     * to save future requests.
     *
     * @private
     */
    _fetchPushConfiguration: function () {
        return this.rpc('/social_push_notifications/fetch_push_configuration').then(function (config) {
            const expirationDate = new Date();
            expirationDate.setDate(expirationDate.getDate() + 7);
            Object.assign(config, {'expirationDate': expirationDate});
            browser.localStorage.setItem(
                'social_push_notifications.notification_request_config',
                JSON.stringify(config)
            );
            return config;
        });
    },

    /**
     * Will register the subscription token into database for later notifications
     *
     * We store the token in the localStorage for 7 days to avoid having to save
     * it every time the user loads a website page.
     *
     * If the token from localStorage is different from the one we are registering, we clean
     * the old one from the registrations.
     *
     * @param {string} token
     */
    _registerToken: function (token) {
        this;

        var pushConfiguration = this._getPushConfiguration();
        if (pushConfiguration && pushConfiguration.token !== token) {
            this.rpc('/social_push_notifications/unregister', {
                token: pushConfiguration.token
            });
        }

        this.rpc('/social_push_notifications/register', {
            token: token
        }).then(function () {
            browser.localStorage.setItem('social_push_notifications.configuration', JSON.stringify({
                'token': token,
            }));
        });
    },

    /**
     * We work with 2 different permission request popups:
     *
     * - The first one is a regular bootstrap popup configurable (title,text,...) from the backend.
     *   It has an accept and a deny buttons. It also closes if the user clicks outside.
     *
     * -> if closed by clicking outside/on cross, will re-open on next page reload
     * -> if closed by clicking 'Deny', will re-open after 7 days on page reload
     * -> if closed by clicking on 'Allow', triggers the second popup.
     *
     * - The second popup is the one opened by the browser when asking for notifications permission.
     *
     * -> if closed by clicking outside/on cross, will re-open the first popup on next page reload
     * -> if closed by clicking on 'Block', we will not be allowed to send notifications to that user.
     *    (TODO awa: give some kind of feedback and show how to go to page settings?
     *     -> might be tricky, probably need a full spec later)
     * -> if closed by clicking on 'Allow', we register a service worker to send notifications.
     *
     * In addition to that, the first popup configuration (title,text,...) is stored into localStorage
     * to avoid having to fetch it on every page reload if the user doesn't accept or deny the popup.
     *
     * The configuration is stored for 7 days to still receive visual updates if the configuration
     * changes on the backend side.
     *
     * @param {String} [nextAskPermissionKeySuffix] optional - Suffix of the cache entry
     * @param {Object} [forcedPopupConfig] optional - Properties that will overwrite the notification request configuration.
     * @param {String} forcedPopupConfig.title optional - Title of the popup.
     * @param {String} forcedPopupConfig.body optional - Body of the popup.
     * @param {String} forcedPopupConfig.delay optional - Delay of the popup.
     * @param {String} forcedPopupConfig.icon optional - Icon of the popup.
     */
    _askPermission: async function (nextAskPermissionKeySuffix, forcedPopupConfig) {
        var self = this;

        var nextAskPermission = browser.localStorage.getItem('social_push_notifications.next_ask_permission' +
            (nextAskPermissionKeySuffix ? '.' + nextAskPermissionKeySuffix : ''));
        if (nextAskPermission && new Date() < new Date(nextAskPermission)) {
            return;
        }

        const { pushConfigurationPromise } = this._getNotificationRequestConfiguration();
        const pushConfiguration = await pushConfigurationPromise;
        if (Object.keys(pushConfiguration).length === 1) {
            return;
        }
        let popupConfig = {
            title: pushConfiguration.notification_request_title,
            body: pushConfiguration.notification_request_body,
            delay: pushConfiguration.notification_request_delay,
            icon: pushConfiguration.notification_request_icon
        };

        if (!popupConfig || !popupConfig.title || !popupConfig.body) {
            return; // this means that the web push notifications are not enabled in the settings
        }
        if (forcedPopupConfig) {
            popupConfig = Object.assign({}, popupConfig, forcedPopupConfig);
        }
        self._showNotificationRequestPopup(popupConfig, pushConfiguration, nextAskPermissionKeySuffix);
    },

    /**
     * Method responsible for the display of the Notification Request Popup.
     * It also reacts the its 'allow' and 'deny' events (see '_askPermission' for details).
     *
     * @param {Object} popupConfig the popup configuration (title,body,...)
     * @param {Object} pushConfig the push configuration
     * @param {String} [nextAskPermissionKeySuffix] optional
     */
    _showNotificationRequestPopup: function (popupConfig, pushConfig, nextAskPermissionKeySuffix) {
        var selector = '.o_social_push_notifications_permission_request';
        if (!popupConfig.title || !popupConfig.body || this.$el.find(selector).length > 0) {
            return;
        }

        var self = this;
        var notificationRequestPopup = new NotificationRequestPopup(this, {
            title: popupConfig.title,
            body: popupConfig.body,
            delay: popupConfig.delay,
            icon: popupConfig.icon
        });
        notificationRequestPopup.appendTo(this.$el);

        notificationRequestPopup.on('allow', null, function () {
            Notification.requestPermission().then(function () {
                if (Notification.permission === "granted") {
                    const messaging = self._initializeFirebaseApp(pushConfig);
                    self._registerServiceWorker(pushConfig, messaging);
                    self._setForegroundNotificationHandler(pushConfig, messaging);
                }
            });
        });

        notificationRequestPopup.on('deny', null, function () {
            var nextAskPermissionDate = new Date();
            nextAskPermissionDate.setDate(nextAskPermissionDate.getDate() + 7);
            browser.localStorage.setItem('social_push_notifications.next_ask_permission' +
                (nextAskPermissionKeySuffix ? '.' + nextAskPermissionKeySuffix : ''),
                nextAskPermissionDate);
        });
    },

    _getPushConfiguration: function () {
        return this._getJSONLocalStorageItem(
            'social_push_notifications.configuration'
        );
    },

    /**
     * Get the notification request configuration.
     *
     * The configuration is first retrieved from local storage if it's still valid.
     * If not, it will be fetched from the server.
     *
     * @returns {Promise, boolean} the push configuration as a promise and a boolean
     * indicating if the configuration was updated.
     *
     * @private
    */
    _getNotificationRequestConfiguration: function () {
        const pushConfiguration = this._getJSONLocalStorageItem(
            'social_push_notifications.notification_request_config'
        );

        const wasUpdated = !this._isConfigurationUpToDate(pushConfiguration);
        const pushConfigurationPromise = wasUpdated ? this._fetchPushConfiguration() :
            Promise.resolve(pushConfiguration);

        return { pushConfigurationPromise, wasUpdated };
    },

    _getJSONLocalStorageItem: function (key) {
        var value = browser.localStorage.getItem(key);
        if (value) {
            return JSON.parse(value);
        }

        return null;
    },

    /**
     * The module will guarantee that no other push notification request for
     * the `nextAskPermissionKeySuffix` key will issued if the user dismissed
     * a request using the same key within the last 7 days.
     *
     * This can be useful in specific context, e.g:
     * When favoriting event.tracks, we want to re-ask the user to enable the push
     * notifications even if the user recently dismisses the default one. By
     * using a custom key, we can issue a new request without having to wait that
     * the 7 days restriction set by the first request expires. When the user
     * dismisses the new request, a 7 days restriction will also be applied to the
     * provided key.
     *
     * @param {String} [nextAskPermissionKeySuffix] Suffix of the cache entry.
     * @param {Object} [forcedPopupConfig] Properties of the popup.
     * @param {String} forcedPopupConfig.title optional - Title of the popup.
     * @param {String} forcedPopupConfig.body optional - Body of the popup.
     * @param {String} forcedPopupConfig.delay optional - Delay of the popup.
     * @param {String} forcedPopupConfig.icon optional - Icon of the popup.
     */
    _onNotificationRequest: async function (nextAskPermissionKeySuffix, forcedPopupConfig) {
        if (Notification.permission !== 'default') {
            return;
        }
        this._askPermission(nextAskPermissionKeySuffix, forcedPopupConfig);
    },
});

export default publicWidget.registry.NotificationWidget;
