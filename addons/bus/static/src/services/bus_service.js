/** @odoo-module **/

import { CrossTab } from '@bus/crosstab_bus';

import { registry } from '@web/core/registry';
import session from 'web.session';

export class BusService extends CrossTab {
    constructor(env, services) {
        super(env, services);

        // properties
        this._audio = null;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Send a notification, and notify once per browser's tab
     *
     * @param {function} [callback] if given callback will be called when user clicks on notification
     * @param {Object} options
     * @param {string} options.message
     * @param {string} options.title
     * @param {string} [options.type] 'info', 'success', 'warning', 'danger' or ''
     */
    sendNotification(options, callback) {
        if (window.Notification && Notification.permission === "granted") {
            if (this.isMasterTab()) {
                try {
                    this._sendNativeNotification(options.title, options.message, callback);
                } catch (error) {
                    // Notification without Serviceworker in Chrome Android doesn't works anymore
                    // So we fallback to the notification service in this case
                    // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
                    if (error.message.indexOf('ServiceWorkerRegistration') > -1) {
                        this.env.services['notification'].add(options.message, options);
                        this._beep();
                    } else {
                        throw error;
                    }
                }
            }
        } else {
            this.env.services['notification'].add(options.message, options);
            if (this.isMasterTab()) {
                this._beep();
            }
        }
    }

    /**
     * Register listeners on notifications received on this bus service
     *
     * @param {Object} receiver
     * @param {function} func
     */
    onNotification() {
        this.on.apply(this, ["notification"].concat(Array.prototype.slice.call(arguments)));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Lazily play the 'beep' audio on sent notification
     *
     * @private
     */
    _beep() {
        if (typeof(Audio) !== "undefined") {
            if (!this._audio) {
                this._audio = new Audio();
                var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                this._audio.src = session.url("/mail/static/src/audio/ting" + ext);
            }
            Promise.resolve(this._audio.play()).catch(_.noop);
        }
    }

    /**
     * Show a browser notification
     *
     * @private
     * @param {string} title
     * @param {string} content
     * @param {function} [callback] if given callback will be called when user clicks on notification
     */
    _sendNativeNotification(title, content, callback) {
        var notification = new Notification(
            // The native Notification API works with plain text and not HTML
            // unescaping is safe because done only at the **last** step
            _.unescape(title),
            {
                body: _.unescape(content),
                icon: "/mail/static/src/img/odoobot_transparent.png"
            });
        notification.onclick = function () {
            window.focus();
            if (this.cancel) {
                this.cancel();
            } else if (this.close) {
                this.close();
            }
            if (callback) {
                callback();
            }
        };
    }
}

export const busService = {
    dependencies: ['notification', 'rpc'],
    start(env, services) {
        return new BusService(env, services);
    },
};
registry.category('services').add('bus_service', busService);
