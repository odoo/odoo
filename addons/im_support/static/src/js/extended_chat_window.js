odoo.define('im_support.ExtendedChatWindow', function (require) {
"use strict";

/**
 * This module includes ExtendedChatWindow to handle the case of the Support
 * channel.
 */


var ExtendedChatWindow = require('mail.ExtendedChatWindow');

ExtendedChatWindow.include({
    /**
     * Overrides to tweak the options in the case of the Support channel (no
     * star, and no input if no operator available).
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        var channel = this.call('chat_manager', 'getChannel', this.channel_id);
        if (channel && channel.supportChannel) {
            this.options.display_stars = false;
            if (!channel.available) {
                this.options.input_less = true;
            }
        }
    },
    /**
     * Overrides to remove the attachment button in the Support channel as this
     * feature does not work in that channel.
     *
     * @note: this feature could be enabled by storing the attachments on the
     * Support server.
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var channel = this.call('chat_manager', 'getChannel', this.channel_id);
        if (channel && channel.supportChannel) {
            this.$('.o_composer .o_composer_button_add_attachment').remove();
        }
        return def;
    },
});

});
