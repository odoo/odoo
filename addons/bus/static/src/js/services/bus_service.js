odoo.define('bus.BusService', function (require) {
"use strict";

var CrossTab = require('bus.CrossTab');
var core = require('web.core');
var ServicesMixin = require('web.ServicesMixin');
const session = require('web.session');

var BusService =  CrossTab.extend(ServicesMixin, {
    dependencies : ['local_storage'],

    // properties
    _audio: null,

    /**
     * As the BusService doesn't extend AbstractService, we have to replicate
     * here what is done in AbstractService
     *
     * @param {Object} env
     */
    init: function (env) {
        this.env = env;
        this._super();
    },

    /**
     * Replicate the behavior of AbstractService:
     *
     * Directly calls the requested service, instead of triggering a
     * 'call_service' event up, which wouldn't work as services have no parent.
     *
     * @param {OdooEvent} ev
     */
    _trigger_up: function (ev) {
        if (ev.name === 'call_service') {
            const payload = ev.data;
            let args = payload.args || [];
            if (payload.service === 'ajax' && payload.method === 'rpc') {
                // ajax service uses an extra 'target' argument for rpc
                args = args.concat(ev.target);
            }
            const service = this.env.services[payload.service];
            const result = service[payload.method].apply(service, args);
            payload.callback(result);
        }
    },
    /**
     * This method is necessary in order for this Class to be used to instantiate services
     *
     * @abstract
     */
    start: function () {},

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
                    // So we fallback to displayNotification() in this case
                    // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
                    if (error.message.indexOf('ServiceWorkerRegistration') > -1) {
                        this.displayNotification(options);
                        this._beep();
                    } else {
                        throw error;
                    }
                }
            }
        } else {
            this.displayNotification(options);
            if (this.isMasterTab()) {
                this._beep();
            }
        }
    },
    /**
     * Register listeners on notifications received on this bus service
     *
     * @param {Object} receiver
     * @param {function} func
     */
    onNotification: function () {
        this.on.apply(this, ["notification"].concat(Array.prototype.slice.call(arguments)));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Lazily play the 'beep' audio on sent notification
     *
     * @private
     */
    _beep: function () {
        if (typeof(Audio) !== "undefined") {
            if (!this._audio) {
                this._audio = new Audio();
                var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                this._audio.src = session.url("/mail/static/src/audio/ting" + ext);
            }
            Promise.resolve(this._audio.play()).catch(_.noop);
        }
    },
    /**
     * Show a browser notification
     *
     * @private
     * @param {string} title
     * @param {string} content
     * @param {function} [callback] if given callback will be called when user clicks on notification
     */
    _sendNativeNotification: function (title, content, callback) {
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
    },

});

core.serviceRegistry.add('bus_service', BusService);

return BusService;

});
