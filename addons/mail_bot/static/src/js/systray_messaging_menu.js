odoo.define('mail_bot.systray.MessagingMenu', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');
var core = require('web.core');

var _t = core._t;

return MessagingMenu.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override so that 'mailbot has a request' is included in the computation
     * of of the counter.
     *
     * @override
     * @private
     * @returns {integer}
     */
    _computeCounter: function () {
        var counter = this._super.apply(this, arguments);
        if (this.call('mailbot_service', 'isRequestingForNativeNotifications')) {
            counter++;
        }
        return counter;
    },
    /**
     * Override so that the mailbot previews are included in the systray
     * messaging menu (e.g. 'OdooBot has a request')
     *
     * @override
     * @private
     * @returns {Promise<Object[]>} resolved with list of previews that are
     *   compatible with the 'mail.Preview' template.
     */
    _getPreviews: function () {
        var mailbotPreviews = this.call('mailbot_service', 'getPreviews', this._filter);
        return this._super.apply(this, arguments).then(function (previews) {
            return _.union(mailbotPreviews, previews);
        });
    },
    /**
     * Handle the response of the user when prompted whether push notifications
     * are granted or denied.
     *
     * Also refreshes the counter after a response from a push notification
     * request. This is useful because the counter contains a part for the
     * OdooBot, and the OdooBot influences the counter by 1 when it requests
     * for notifications. This should no longer be the case when push
     * notifications are either granted or denied.
     *
     * @private
     * @param {string} value
     */
    _handleResponseNotificationPermission: function (value) {
        this.call('mailbot_service', 'removeRequest');
        if (value !== 'granted') {
            this.call('bus_service', 'sendNotification', _t('Permission denied'),
                _t('Odoo will not have the permission to send native notifications on this device.'));
        }
        this._updateCounter();
    },
    /**
     * Display the browser notification request dialog when the user clicks on
     * systray's corresponding notification
     *
     * @private
     */
    _requestNotificationPermission: function () {
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        this.$('.o_mail_navbar_request_permission').slideUp();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Override so that it handles preview related to OdooBot
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPreview: function (ev) {
        var previewID = $(ev.currentTarget).data('preview-id');
        if (previewID === 'request_notification') {
            this._requestNotificationPermission();
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Override so that it handles clicking on 'mark as read' similarly to
     * requesting push notification permission.
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPreviewMarkAsRead: function (ev) {
        ev.stopPropagation();
        var $preview = $(ev.currentTarget).closest('.o_mail_preview');
        var previewID = $preview.data('preview-id');
        if (previewID === 'request_notification') {
            this._requestNotificationPermission();
        } else {
            this._super.apply(this, arguments);
        }
    }
});

});
