odoo.define('website.mobile', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var website = require('website.website');

var _t = core._t;

var MobilePreviewDialog = Dialog.extend({
    template: 'website.mobile_preview',

    init: function () {
        this._super.apply(this, arguments);
        this.mobile_src = $.param.querystring(window.location.href, 'mobilepreview');
    },

    start: function () {
        var self = this;
        this.$modal.addClass('oe_mobile_preview');
        this.$modal.on('click', '.modal-header', function () {
            self.$el.toggleClass('o_invert_orientation');
        });
        this.$iframe = this.$('iframe');
        this.$iframe.on('load', function (e) {
            self.$iframe.contents().find('body').removeClass('o_connected_user');
            self.$iframe.contents().find('#oe_main_menu_navbar, #o_website_add_page_modal').remove();
        });

        return this._super.apply(this, arguments);
    },
});

website.TopBar.include({
    start: function () {
        var self = this;
        this.$el.on('click', 'a[data-action=show-mobile-preview]', function () {
            new MobilePreviewDialog(self, {
                title: _t('Mobile preview') + " <span class='fa fa-refresh'/>",
            }).open();
        });
        return this._super();
    },
});

});
