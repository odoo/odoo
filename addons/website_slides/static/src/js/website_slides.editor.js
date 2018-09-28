odoo.define('website_slides.editor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide: '_createNewSlide',
    }),
    xmlDependencies: WebsiteNewMenu.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slides.xml']
    ),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about in which channel to create a new slide,
     * and redirects the user to this channel with the "new slide" popup open.
     *
     * @private
     * @returns {Deferred} Unresolved if there is a redirection
     */
    _createNewSlide: function () {
        var self = this;
        return this._rpc({
            model: 'slide.channel',
            method: 'list_all',
            args: [[]],
        }).then(function (data) {
            var def = $.Deferred();
            new Dialog(self, {
                title: _t("New slide"),
                subtitle: _t("On which channel do you want to add a slide?"),
                size: 'medium',
                $content: QWeb.render('website.slide.create', data),
                buttons: [{
                    text: _t("Select"),
                    classes: 'btn-primary',
                    click: function () {
                        var channel_url = this.$("option:selected").val();
                        if (channel_url) {
                            window.location.href = channel_url + '?enable_slide_upload';
                        } else {
                            def.reject();
                        }
                    }
                }, {
                    text: _t("Cancel"), close: true
                },]
            }).open()
                .on('closed', def.resolve.bind(def));

            return def;
        });
    },
});
});
