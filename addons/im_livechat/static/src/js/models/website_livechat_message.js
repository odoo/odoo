odoo.define('im_livechat.model.WebsiteLivechatMessage', function (require) {
"use strict";

var AbstractMessage = require('mail.model.AbstractMessage');

/**
 * This is a message that is handled by im_livechat, without making use of the
 * mail.Manager. The purpose of this is to make im_livechat compatible with
 * mail.widget.Thread.
 *
 * @see mail.model.AbstractMessage for more information.
 */
var WebsiteLivechatMessage =  AbstractMessage.extend({

    /**
     * @param {im_livechat.im_livechat.LivechatButton} parent
     * @param {Object} data
     * @param {Object} options
     * @param {string} options.default_username
     * @param {string} options.serverURL
     */
    init: function (parent, data, options) {
        this._super.apply(this, arguments);

        this._defaultUsername = options.default_username;
        this._serverURL = options.serverURL;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @override
     * @return {string}
     */
    getAvatarSource: function () {
        var source = this._serverURL;
        if (this.hasAuthor()) {
            source += '/web/image/res.partner/' + this.getAuthorID() + '/image_small';
        } else {
            source += '/mail/static/src/img/smiley/avatar.jpg';
        }
        return source;
    },
    /**
     * Get the text to display for the author of the message
     *
     * Rule of precedence for the displayed author::
     *
     *      author name > default usernane
     *
     * @override
     * @return {string}
     */
    getDisplayedAuthor: function () {
        return this._super.apply(this, arguments) || this._defaultUsername;
    },

});

return WebsiteLivechatMessage;

});
