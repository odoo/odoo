odoo.define('im_support.systray.MessagingMenu', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');

var _t = core._t;
var SUPPORT_CHANNEL_ID = 'SupportChannel';

// Disable Support in mobile for design purposes (for now at least), and don't
// add it to the messaging dropdown if it isn't available
if (config.device.isMobile || !session.support_token || !session.support_origin) {
    return;
}

/**
 * This module adds a fake Support channel in the messaging menu of the systray.
 */
MessagingMenu.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.supportChannel = {
            id: SUPPORT_CHANNEL_ID,
            name: _t("Support"),
            imageSRC: '/mail/static/src/img/odoo_o.png',
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
            self.$('.o_mail_systray_dropdown_bottom').addClass('o_mail_systray_dropdown_items');
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
    _onClickPreview: function (ev) {
        var id = $(ev.currentTarget).data('preview-id');
        if (id === SUPPORT_CHANNEL_ID) {
            this.call('mail_service', 'startSupportLivechat');
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
