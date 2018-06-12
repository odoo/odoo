odoo.define('im_support.Discuss', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

/**
 * This module includes Discuss to handle the case of the Support channel.
 */
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
        if (this._thread.getType() === 'support_channel') {
            options.displayStars = false;
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
    _setThread: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $buttonAddAttachment = self._basicComposer.$('.o_composer_button_add_attachment');
            if (self._thread.getType() === 'support_channel') {
                if (!self._thread.isAvailable()) {
                    self._basicComposer.do_hide();
                }
                $buttonAddAttachment.toggleClass('o_hidden', true);
            } else {
                $buttonAddAttachment.toggleClass('o_hidden', false);
            }
        });
    },
    /**
     * Overrides to handle the Support channel case (hide all buttons).
     *
     * @override
     * @private
     */
    _updateControlPanelButtons: function (thread) {
        this._super.apply(this, arguments);
        if (thread.getType() === 'support_channel') {
            this.$buttons.find('button').hide();
        }
    },
});

});
