odoo.define('bus.BusService', function (require) {
"use strict";

var bus = require('bus.bus').bus;

var AbstractService = require('web.AbstractService');
var core = require('web.core');

var BusService =  AbstractService.extend({
    name: 'bus_service',
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.bus = bus;
        this._audio = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the bus
     *
     * @return {web.Bus} the longpoll bus
     */
    getBus: function () {
        return this.bus;
    },

    /**
     * Send a notification, and notify once per browser's tab
     *
     * @param {string} title
     * @param {string} content
     */
    sendNotification: function (title, content) {
        if (window.Notification && Notification.permission === "granted") {
            if (this.bus.is_master) {
                this._sendNativeNotification(title, content);
            }
        } else {
            this.do_notify(title, content);
            if (this.bus.is_master) {
                this._beep();
            }
        }
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
            this._audio.play();
        }
    },
    /**
     * Show a browser notification
     *
     * @private
     * @param {string} title
     * @param {string} content
     */
    _sendNativeNotification: function (title, content) {
        var notification = new Notification(title, {body: content, icon: "/mail/static/src/img/odoo_o.png"});
        notification.onclick = function () {
            window.focus();
            if (this.cancel) {
                this.cancel();
            } else if (this.close) {
                this.close();
            }
        };
    },

});

core.serviceRegistry.add('bus_service', BusService);

return BusService;

});
