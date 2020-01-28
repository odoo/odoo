odoo.define('bus.BusService', function (require) {
"use strict";

var CrossTab = require('bus.CrossTab');
var { serviceRegistry } = require('web.core');

class BusService extends CrossTab {

    /**
     * This method is necessary in order for this Class to be used to instantiate services
     *
     * @abstract
     */
    start() {}

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Send a notification, and notify once per browser's tab
     *
     * @param {string} title
     * @param {string} message
     * @param {function} [callback] if given callback will be called when user clicks on notification
     */
    sendNotification(title, message, callback) {
        if (window.Notification && window.Notification.permission === "granted") {
            if (this.isMasterTab()) {
                this._sendNativeNotification(title, message, callback);
            }
        } else {
            this.env.services.notification.notify({ title, message });
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
                this._audio = new window.Audio();
                var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                this._audio.src = this.env.session.url("/mail/static/src/audio/ting" + ext);
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
        var notification = new window.Notification(title, {
            body: content,
            icon: "/mail/static/src/img/odoobot_transparent.png",
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

Object.assign(BusService, {
    dependencies : ['local_storage'],
    // properties
    _audio: null,
});

serviceRegistry.add('bus', BusService);

return BusService;

});
