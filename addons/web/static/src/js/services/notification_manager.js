odoo.define('web.NotificationManager', function (require) {
"use strict";

/**
 * NotificationManager
 *
 * The NotificationManager is simply a widget that will be instantiated by the
 * web client to display notifications in the top/right part of the screen.
 *
 * If you want to display such a notification, you probably do not want to do it
 * by using this file. The proper way is to use the do_warn or do_notify
 * methods on the Widget class.
 *
 * @todo This class should be converted into a proper service. Need the right
 * service API to do it.
 */

var Notification = require('web.Notification');
var Widget = require('web.Widget');

var NotificationManager = Widget.extend({
    className: 'o_notification_manager',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Display a notification at the appropriate location, and returns the
     * reference to the same widget (useful to get back a reference).
     *
     * Note that this method does not wait for the appendTo method to complete.
     *
     * @param {Notification} notification
     * @returns {Notification}
     */
    display: function (notification) {
        notification.appendTo(this.$el);
        return notification;
    },
    /**
     * Will display a notification of type 'notification'
     *
     * @param {string} title
     * @param {string} text
     * @param {boolean} sticky
     * @returns {Notification}
     */
    notify: function (title, text, sticky) {
        return this._display(title, text, sticky, 'notification');
    },
    /**
     * Will display a notification of type 'warning'
     *
     * @param {string} title
     * @param {string} text
     * @param {boolean} sticky
     * @returns {Notification}
     */
    warn: function (title, text, sticky) {
        return this._display(title, text, sticky, 'warning');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Display a notification
     *
     * @private
     * @param {string} title
     * @param {string} text
     * @param {boolean} sticky
     * @param {string} type either 'notification' or 'warning'
     * @returns {Notification}
     */
    _display: function (title, text, sticky, type) {
        return this.display(new Notification(this, {
            title: title,
            text: text,
            sticky: sticky,
            type: type,
        }));
    }
});

return NotificationManager;

});
