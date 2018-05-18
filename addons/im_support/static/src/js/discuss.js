odoo.define('im_support.chat_discuss', function (require) {
"use strict";

/**
 * This module includes Discuss to handle the case of the Support channel.
 */

var Discuss = require('mail.chat_discuss');

Discuss.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overrides to hide stars in the Support channel, as this feature does not
     * work in that channel.
     *
     * @override
     * @private
     */
    _getThreadRenderingOptions: function () {
        var options = this._super.apply(this, arguments);
        if (this.channel.supportChannel) {
            options.display_stars = false;
        }
        return options;
    },
    /**
     * Overrides to hide the attachment button in the composer of the Support
     * channel, as this feature does not work in that channel. Also hides the
     * composer when no operator is available.
     *
     * @override
     * @private
     */
    _setChannel: function (channel) {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $buttonAddAttachment = self.basicComposer.$('.o_composer_button_add_attachment');
            if (channel.supportChannel) {
                if (!channel.available) {
                    self.basicComposer.do_hide();
                }
                $buttonAddAttachment.hide();
            } else {
                $buttonAddAttachment.show();
            }
        });
    },
    /**
     * Overrides to handle the Support channel case (hide all buttons).
     *
     * @override
     * @private
     */
    _updateControlPanelButtons: function (channel) {
        this._super.apply(this, arguments);
        if (channel.supportChannel) {
            this.$buttons.find('button').hide();
        }
    },
});

});
