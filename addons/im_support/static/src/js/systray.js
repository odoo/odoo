odoo.define('im_support.systray', function (require) {
"use strict";

/**
 * This module adds a fake Support channel in the messaging menu of the systray.
 */

var mailSystray = require('mail.systray');

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');

var _t = core._t;
var MessagingMenu = mailSystray.MessagingMenu;
var SUPPORT_CHANNEL_ID = 'SupportChannel';

// Disable Support in mobile for design purposes (for now at least), and don't
// add it to the messaging dropdown if it isn't available
if (config.device.isMobile || !session.support_token || !session.support_origin) {
    return;
}

MessagingMenu.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.supportChannel = {
            id: SUPPORT_CHANNEL_ID,
            name: _t('Support'),
            image_src: '/mail/static/src/img/odoo_o.png',
        };
    },
    /**
     * Overrides to add a className to the bottom part of the dropdown
     * (containing the Support channel), so that the css rules apply. This
     * className can't be added directly in the template, otherwise
     * this.$channels_preview would be a nodeset containing the bottom part as
     * well, and it will cause rendering issues when the dropdown is rerendered.
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_mail_navbar_dropdown_bottom').addClass('o_mail_navbar_dropdown_channels');
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Overrides to handle the click on the fake Support channel.
     *
     * @override
     * @private
     */
    _onClickChannel: function (ev) {
        var channelID = $(ev.currentTarget).data('channel_id');
        if (channelID === SUPPORT_CHANNEL_ID) {
            this.call('chat_manager', 'startSupportLivechat');
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
