odoo.define('bus.WebClient', function (require) {
    "use strict";

    const core = require('web.core');
    const WebClient = require('web.WebClient');

    const _t = core._t;

    WebClient.include({

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Detects the presence of assets in DOM's HEAD
         *
         * @override
         */
        async start() {
            this._assetsChangedNotificationId = null;
            this._assets = {};
            await this._super(...arguments);
        },
        /**
         * Assigns handler to bus notification
         *
         * @override
         */
        show_application() {
            const shown = this._super(...arguments);
            document.querySelectorAll('*[data-asset-xmlid]').forEach(el => {
                this._assets[el.getAttribute('data-asset-xmlid')] = el.getAttribute('data-asset-version');
            });
            this.call('bus_service', 'onNotification', this, this._onNotification);
            this.call('bus_service', 'addChannel', 'bundle_changed');
            return shown;
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Displays one notification on user's screen when assets have changed
         *
         * @private
         */
        _displayBundleChangedNotification() {
            if (!this._assetsChangedNotificationId) {
                // Wrap the notification inside a delay.
                // The server may be overwhelmed with recomputing assets
                // We wait until things settle down
                clearTimeout(this._bundleNotifTimerID);
                this._bundleNotifTimerID = setTimeout(() => {
                    this._assetsChangedNotificationId = this.call('notification', 'notify', {
                        title: _t('Refresh'),
                        message: _t('The page appears to be out of date.'),
                        sticky: true,
                        onClose: () => {
                            this._assetsChangedNotificationId = null;
                        },
                        buttons: [{
                            text: _t('Refresh'),
                            primary: true,
                            click: () => {
                                window.location.reload(true);
                            }
                        }],
                    });
                }, this._getBundleNotificationDelay());
            }
        },
        /**
         * Computes a random delay to avoid hammering the server
         * when bundles change with all the users reloading
         * at the same time
         *
         * @private
         * @return {number} delay in milliseconds
         */
        _getBundleNotificationDelay() {
            return 10000 + Math.floor(Math.random()*50) * 1000;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Reacts to bus's notification
         *
         * @private
         * @param {Array} notifications: list of received notifications
         */
        _onNotification(notifications) {
            for (const notif of notifications) {
                if (notif[0][1] === 'bundle_changed') {
                    const bundleXmlId = notif[1][0];
                    const bundleVersion = notif[1][1];
                    if (bundleXmlId in this._assets && bundleVersion !== this._assets[bundleXmlId]) {
                        this._displayBundleChangedNotification();
                        break;
                    }
                }
            }
        }
    });
});
