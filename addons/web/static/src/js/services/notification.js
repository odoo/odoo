odoo.define('web.NotificationService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var Notification = require('web.Notification');
var core = require('web.core');
var id = 0;

/**
 * webNotification
 *
 * The webNotification is simply a service used to display notifications in
 * the top/right part of the screen.
 *
 * If you want to display such a notification, you probably do not want to do it
 * by using this file. The proper way is to use the do_warn or do_notify
 * methods on the Widget class.
 */

var WebNotification = AbstractService.extend({
    name: 'web.Notification',

    custom_events: {
        close: '_onCloseNotification',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.notifications = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Display a notification at the appropriate location, and returns the
     * reference id to the same widget.
     *
     * Note that this method does not wait for the appendTo method to complete.
     *
     * @param {Object} params
     * @param {string} params.title notification title
     * @param {string} params.message notification main message
     * @param {string} params.type 'notification' or 'warning'
     * @param {boolean} [params.sticky=false] if true, the notification will stay
     *   visible until the user clicks on it.
     * @param {string} [params.className] className to add on the dom
     * @param {function} [params.onClose] callback when the user click on the x
     *   or when the notification is auto close (no sticky)
     * @param {Array<Object>} params.buttons
     * @param {function} params.buttons[0].click callback on click
     * @param {Boolean} [params.buttons[0].primary] display the button as primary
     * @param {string} [params.buttons[0].text] button label
     * @param {string} [params.buttons[0].icon] font-awsome className or image src
     * @returns {Number} notification id
     */
    notify: function (options) {
        if (!this.$el) {
            this.$el = $('<div class="o_notification_manager"/>');
            this.$el.prependTo('body');
        }
        var notification = this.notifications[++id] = new Notification(this, options);
        notification.appendTo(this.$el);
        return id;
    },
    /**
     *
     * @param {Number} notificationId
     * @param {boolean} [silent=false] if true, the notification does not call
     *   onClose callback
     */
    close: function (notificationId, silent) {
        var notification = this.notifications[notificationId];
        if (!notification) {
            return;
        }
        notification.close(silent);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseNotification: function (ev) {
        ev.stopPropagation();
        for (var notificationId in this.notifications) {
            if (this.notifications[notificationId] === ev.target) {
                delete this.notifications[notificationId];
                break;
            }
        }
    },
});


core.serviceRegistry.add('web.Notification', WebNotification);


return WebNotification;
});
