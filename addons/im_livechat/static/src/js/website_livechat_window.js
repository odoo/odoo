odoo.define('im_livechat.WebsiteLivechatWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see mail.AbstractThreadWindow for more information
 */
var LivechatWindow = AbstractThreadWindow.extend({
    events: _.extend(AbstractThreadWindow.prototype.events, {
        'input .o_composer_text_field': '_onInput',
    }),
    /**
     * @override
     * @param {im_livechat.im_livechat.LivechatButton} parent
     * @param {im_livechat.model.WebsiteLivechat} thread
     * @param {Object} [options={}]
     * @param {string} [options.headerBackgroundColor]
     * @param {string} [options.titleColor]
     */
    init(parent, thread, options={}) {
        this._super.apply(this, arguments);
        this._thread = thread;
    },
    /**
     * @override
     * @return {Promise}
     */
    async start() {
        await this._super(...arguments);
        if (this.options.headerBackgroundColor) {
            this.$('.o_thread_window_header').css('background-color', this.options.headerBackgroundColor);
        }
        if (this.options.titleColor) {
            this.$('.o_thread_window_header').css('color', this.options.titleColor);
        }
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        this.trigger_up('close_chat_window');
    },
    /**
     * Replace the thread content with provided new content
     *
     * @param {$.Element} $element
     */
    replaceContentWith: function ($element) {
        $element.replace(this._threadWidget.$el);
    },
    /**
     * Warn the parent widget (LivechatButton)
     *
     * @override
     * @param {boolean} folded
     */
    toggleFold: function () {
        this._super.apply(this, arguments);
        this.trigger_up('save_chat_window');
        this.updateVisualFoldState();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        this.trigger_up('post_message_chat_window', { messageData: messageData });
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the input in the composer changes
     *
     * @private
     */
    _onInput: function () {
        if (this.hasThread() && this._thread.hasTypingNotification()) {
            const typingText = this.$input.val().trim();
            const isTyping = typingText.length > 0;
            this._thread.setMyselfTyping({ typing: isTyping, typingText: typingText });
        }
    },
});

return LivechatWindow;

});
