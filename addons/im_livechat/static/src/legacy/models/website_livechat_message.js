/** @odoo-module **/

import AbstractMessage from '@im_livechat/legacy/models/abstract_message';

/**
 * This is a message that is handled by im_livechat, without making use of the
 * mail.Manager. The purpose of this is to make im_livechat compatible with
 * mail.widget.Thread.
 *
 * @see @im_livechat/legacy/models/abstract_message for more information.
 */
const WebsiteLivechatMessage = AbstractMessage.extend({

    /**
     * @param {@im_livechat/legacy/widgets/livechat_button} parent
     * @param {Object} data
     * @param {Object} options
     * @param {string} options.default_username
     * @param {string} options.serverURL
     */
    init(parent, data, options) {
        this._super(...arguments);

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
     getAvatarSource() {
        let source = this._serverURL;
        if (this.hasAuthor()) {
            source += `/im_livechat/operator/${this.getAuthorID()}/avatar`;
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
    getDisplayedAuthor() {
        return this._super(...arguments) || this._defaultUsername;
    },

});

export default WebsiteLivechatMessage;
