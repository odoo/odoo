odoo.define('bus.BusService', function (require) {
"use strict";

var CrossTab = require('bus.CrossTab');
var core = require('web.core');
var ServicesMixin = require('web.ServicesMixin');

var BusService =  CrossTab.extend(ServicesMixin, {
    dependencies : ['local_storage'],

    // properties
    _audio: null,

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
     * @param {string} title
     * @param {string} content
     * @param {function} [callback] if given callback will be called when user clicks on notification
     */
    sendNotification: function (title, content, callback) {
        if (window.Notification && Notification.permission === "granted") {
            if (this.isMasterTab()) {
                try {
                    this._sendNativeNotification(title, content, callback);
                } catch (error) {
                    // Notification without Serviceworker in Chrome Android doesn't works anymore
                    // So we fallback to do_notify() in this case
                    // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
                    if (error.message.indexOf('ServiceWorkerRegistration') > -1) {
                        this.do_notify(title, content);
                        this._beep();
                    } else {
                        throw error;
                    }
                }
            }
        } else {
            this.do_notify(title, content);
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
                var session = this.getSession();
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
        var notification = new Notification(title, {body: content, icon: "/mail/static/src/img/odoobot_transparent.png"});
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
