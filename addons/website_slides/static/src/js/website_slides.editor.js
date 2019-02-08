odoo.define('website_slides.editor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide_channel: '_createNewSlideChannel',
    }),
    xmlDependencies: WebsiteNewMenu.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slide_channel.xml']
    ),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Display the popup to create a new slide channel,
     * and redirects the user to this channel.
     *
     * @private
     * @returns {Deferred} Unresolved if there is a redirection
     */
     _createNewSlideChannel: function () {
        var def = $.Deferred();
        var dialog = new Dialog(this, {
            title: _t("New Channel Slide"),
            size: 'medium',
            $content: QWeb.render('website.slide.channel.create', {csrf_token: odoo.csrf_token}),
            buttons: [{
                text: _t("Create"),
                classes: 'btn-primary',
                click: function () {
                    var $form = dialog.$("#slide_channel_add_form");
                    $form.submit()
                }
            }, {
                text: _t("Discard"), close: true
            },]
        })
        dialog.open();
        dialog.on('closed', this, function() {
            def.resolve();
        });

        return def;
     },
});
});
