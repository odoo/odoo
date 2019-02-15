odoo.define('website_slides.editor', function (require) {
"use strict";

var WebsiteNewMenu = require('website.newMenu');
var UploadChannel = require('website_slides.upload_channel');


WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide_channel: '_createNewSlideChannel',
    }),
    xmlDependencies: WebsiteNewMenu.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slides_channel.xml']
    ),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Displays the popup to create a new slide channel and redirects the user to this channel.
     *
     * @private
     * @returns {Deferred} Unresolved if there is a redirection
     */
     _createNewSlideChannel: function () {
        var def = $.Deferred();
        var dialog = new UploadChannel.ChannelCreateDialog(this, {});
        dialog.open();
        dialog.on('closed', this, function() {
            def.resolve();
        });
        return def;
     },
});
});
