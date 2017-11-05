odoo.define('website.mobile', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

var MobilePreviewDialog = Dialog.extend({
    /**
     * Tweaks the modal so that it appears as a phone and modifies the iframe
     * rendering to show more accurate mobile view.
     *
     * @override
     */
    start: function () {
        var self = this;
        this.$modal.addClass('oe_mobile_preview');
        this.$modal.on('click', '.modal-header', function () {
            self.$el.toggleClass('o_invert_orientation');
        });
        this.$iframe = $('<iframe/>', {
            id: 'mobile-viewport',
            src: $.param.querystring(window.location.href, 'mobilepreview'),
        });
        this.$iframe.on('load', function (e) {
            self.$iframe.contents().find('body').removeClass('o_connected_user');
            self.$iframe.contents().find('#oe_main_menu_navbar').remove();
        });
        this.$iframe.appendTo(this.$el);

        return this._super.apply(this, arguments);
    },
});

var MobileMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        'show-mobile-preview': '_onMobilePreviewClick',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the mobile action is triggered -> instantiate the mobile
     * preview dialog.
     *
     * @private
     */
    _onMobilePreviewClick: function () {
        new MobilePreviewDialog(this, {
            title: _t('Mobile preview') + ' <span class="fa fa-refresh"/>',
        }).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(MobileMenu, '#mobile-menu');

return {
    MobileMenu: MobileMenu,
    MobilePreviewDialog: MobilePreviewDialog,
};
});
