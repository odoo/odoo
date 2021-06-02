odoo.define('im_support.ThreadWindow', function (require) {
"use strict";

/**
 * This module includes ThreadWindow to handle the case of the Support channel.
 */
var ThreadWindow = require('mail.ThreadWindow');

ThreadWindow.include({
    /**
     * Overrides to tweak the options in the case of the Support channel (no
     * star).
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        var channel = this.call('mail_service', 'getChannel', this._getThreadID());
        if (channel && channel.getType() === 'support_channel') {
            this.options.displayStars = false;
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
        var channel = this.call('mail_service', 'getChannel', this._getThreadID());
        if (channel && channel.getType() === 'support_channel') {
            this.$('.o_composer .o_composer_button_add_attachment').remove();
            if (!channel.isAvailable()) {
                this.$('.o_thread_composer').remove();
            }
        }
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overrides to prevent from displaying a composer if there is no operator
     * available.
     *
     * @override
     * @private
     */
    _needsComposer: function () {
        var channel = this.call('mail_service', 'getChannel', this._getThreadID());
        if (
            channel &&
            channel.getType() === 'support_channel' &&
            !channel.isAvailable()
        ) {
            return false;
        }
        return this._super.apply(this, arguments);
    },
});

});
