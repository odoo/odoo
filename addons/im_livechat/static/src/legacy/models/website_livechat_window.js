/** @odoo-module **/

import AbstractThreadWindow from '@im_livechat/legacy/widgets/abstract_thread_window/abstract_thread_window';

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see @im_livechat/legacy/widgets/abstract_thread_window for more information
 */
const LivechatWindow = AbstractThreadWindow.extend({
    events: Object.assign(AbstractThreadWindow.prototype.events, {
        'input .o_composer_text_field': '_onInput',
    }),
    /**
     * @override
     * @param {@im_livechat/legacy/widgets/livechat_button} parent
     * @param {@im_livechat/legacy/models/website_livechat} thread
     * @param {Object} [options={}]
     * @param {string} [options.headerBackgroundColor]
     * @param {string} [options.titleColor]
     */
    init(parent, thread, options = {}) {
        this._super(...arguments);
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
    close() {
        this.trigger_up('close_chat_window');
    },
    /**
     * Replace the thread content with provided new content
     *
     * @param {$.Element} $element
     */
    replaceContentWith($element) {
        $element.replace(this._threadWidget.$el);
    },
    /**
     * Warn the parent widget (LivechatButton)
     *
     * @override
     * @param {boolean} folded
     */
    toggleFold() {
        this._super(...arguments);
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
    _postMessage(messageData) {
        this.trigger_up('post_message_chat_window', { messageData });
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the input in the composer changes
     *
     * @private
     */
    _onInput() {
        if (this.hasThread() && this._thread.hasTypingNotification()) {
            const isTyping = this.$input.val().length > 0;
            this._thread.setMyselfTyping({ typing: isTyping });
        }
    },
});

export default LivechatWindow;
