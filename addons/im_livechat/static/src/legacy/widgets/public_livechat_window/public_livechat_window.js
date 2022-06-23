/** @odoo-module **/

import ThreadWidget from '@im_livechat/legacy/widgets/thread/thread';

import config from 'web.config';
import { _t, qweb } from 'web.core';
import Widget from 'web.Widget';

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see @im_livechat/legacy/widgets/public_livechat_window/public_livechat_window for more information
 */
const PublicLivechatWindow = Widget.extend({
    FOLD_ANIMATION_DURATION: 200, // duration in ms for (un)fold transition
    HEIGHT_OPEN: '400px', // height in px of thread window when open
    HEIGHT_FOLDED: '34px', // height, in px, of thread window when folded
    template: 'im_livechat.legacy.PublicLivechatWindow',
    events: {
        'click .o_thread_window_close': '_onClickClose',
        'click .o_thread_window_title': '_onClickFold',
        'click .o_composer_text_field': '_onComposerClick',
        'click .o_mail_thread': '_onThreadWindowClicked',
        'keydown .o_composer_text_field': '_onKeydown',
        'keypress .o_composer_text_field': '_onKeypress',
        'input .o_composer_text_field': '_onInput',
    },
    custom_events: {
        document_viewer_closed: '_onDocumentViewerClose',
    },
    /**
     * @param {Widget} parent
     * @param {@im_livechat/legacy/models/public_livechat} thread
     * @param {Object} [options={}]
     * @param {string} [options.headerBackgroundColor]
     * @param {string} [options.titleColor]
     */
    init(parent, thread, options) {
        this._super(parent);

        this.options = _.defaults(options || {}, {
            autofocus: true,
            displayStars: true,
            displayReplyIcons: false,
            displayNotificationIcons: false,
            placeholder: _t("Say something"),
        });

        this._hidden = false;
        this._thread = thread || null;

        this._debouncedOnScroll = _.debounce(this._onScroll.bind(this), 100);

        if (!this.hasThread()) {
            // internal fold state of thread window without any thread
            this._folded = false;
        }
        this._thread = thread;
    },
    /**
     * @override
     * @return {Promise}
     */
    async start() {
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_thread_window_header');
        const options = {
            displayMarkAsRead: false,
            displayStars: this.options.displayStars,
        };
        if (this._thread && this._thread._type === 'document_thread') {
            options.displayDocumentLinks = false;
        }
        this._threadWidget = new ThreadWidget(this, options);

        // animate the (un)folding of thread windows
        this.$el.css({ transition: 'height ' + this.FOLD_ANIMATION_DURATION + 'ms linear' });
        if (this.isFolded()) {
            this.$el.css('height', this.HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this._focusInput();
        }
        if (!config.device.isMobile) {
            const margin_dir = _t.database.parameters.direction === "rtl" ? "margin-left" : "margin-right";
            this.$el.css(margin_dir, $.position.scrollbarWidth());
        }
        const def = this._threadWidget.replace(this.$('.o_thread_window_content')).then(() => {
            this._threadWidget.$el.on('scroll', this, this._debouncedOnScroll);
        });
        await Promise.all([this._super(), def]);
        if (this.options.headerBackgroundColor) {
            this.$('.o_thread_window_header').css('background-color', this.options.headerBackgroundColor);
        }
        if (this.options.titleColor) {
            this.$('.o_thread_window_header').css('color', this.options.titleColor);
        }
    },
    /**
     * @override
     */
    do_hide() {
        this._hidden = true;
        this._super(...arguments);
    },
    /**
     * @override
     */
    do_show() {
        this._hidden = false;
        this._super(...arguments);
    },
    /**
     * @override
     */
    do_toggle(display) {
        this._hidden = _.isBoolean(display) ? !display : !this._hidden;
        this._super(...arguments);
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
     * States whether this thread window is related to a thread or not.
     *
     * This is useful in order to provide specific behaviour for thread windows
     * without any thread, e.g. let them open a thread from this "blank" thread
     * window.
     *
     * @returns {boolean}
     */
    hasThread() {
        return !! this._thread;
    },
    /**
     * Get the ID of the thread window, which is equivalent to the ID of the
     * thread related to this window
     *
     * @returns {integer|string}
     */
    getID() {
        return this._getThreadID();
    },
    /**
     * @returns {mail.model.Thread|undefined}
     */
    getThread() {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread;
    },
    /**
     * Get the status of the thread, such as the im status of a DM chat
     * ('online', 'offline', etc.). If this window has no thread, returns
     * `undefined`.
     *
     * @returns {string|undefined}
     */
    getThreadStatus() {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread.getStatus();
    },
    /**
     * Get the title of the thread window, which usually contains the name of
     * the thread.
     *
     * @returns {string}
     */
    getTitle() {
        if (!this.hasThread()) {
            return _t("Undefined");
        }
        return this._thread.getTitle();
    },
    /**
     * Get the unread counter of the related thread. If there are no thread
     * linked to this window, returns 0.
     *
     * @returns {integer}
     */
    getUnreadCounter() {
        if (!this.hasThread()) {
            return 0;
        }
        return this._thread.getUnreadCounter();
    },
    /**
     * Tells whether the bottom of the thread in the thread window is visible
     * or not.
     *
     * @returns {boolean}
     */
    isAtBottom() {
        return this._threadWidget.isAtBottom();
    },
    /**
     * State whether the related thread is folded or not. If there are no
     * thread related to this window, it means this is the "blank" thread
     * window, therefore we use the internal folded state.
     *
     * @returns {boolean}
     */
    isFolded() {
        if (!this.hasThread()) {
            return this._folded;
        }
        return this._thread.isFolded();
    },
    /**
     * States whether the thread window is hidden or not.
     *
     * @returns {boolean}
     */
    isHidden() {
        return this._hidden;
    },
    /**
     * States whether the current environment is in mobile or not. This is
     * useful in order to customize the template rendering for mobile view.
     *
     * @returns {boolean}
     */
    isMobile() {
        return config.device.isMobile;
    },
    /**
     * States whether the input of the thread window should be displayed or not.
     * By default, any thread window with a thread needs a composer.
     *
     * @returns {boolean}
     */
    needsComposer() {
        return this.hasThread();
    },
    /**
     * Render the thread window
     */
    render() {
        this.renderHeader();
        if (this.hasThread()) {
            this._threadWidget.render(this._thread, { displayLoadMore: false });
        }
    },
    /**
     * Render the header of this thread window.
     * This is useful when some information on the header have be updated such
     * as the status or the title of the thread that have changed.
     *
     * @private
     */
    renderHeader() {
        const options = this._getHeaderRenderingOptions();
        this.$header.html(
            qweb.render('im_livechat.legacy.PublicLivechatWindow.HeaderContent', options));
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
     * Scroll to the bottom of the thread in the thread window
     */
    scrollToBottom() {
        this._threadWidget.scrollToBottom();
    },
    /**
     * Toggle the fold state of this thread window. Also update the fold state
     * of the thread model. If the boolean parameter `folded` is provided, it
     * folds/unfolds the window when it is set/unset.
     *
     * Warn the parent widget (LivechatButton)
     *
     * @param {boolean} [folded] if not a boolean, toggle the fold state.
     *   Otherwise, fold/unfold the window if set/unset.
     */
    toggleFold(folded) {
        if (!_.isBoolean(folded)) {
            folded = !this.isFolded();
        }
        this._updateThreadFoldState(folded);
        this.trigger_up('save_chat_window');
        this.updateVisualFoldState();
    },
    /**
     * Update the visual state of the window so that it matched the internal
     * fold state. This is useful in case the related thread has its fold state
     * that has been changed.
     */
    updateVisualFoldState() {
        if (!this.isFolded()) {
            this._threadWidget.scrollToBottom();
            if (this.options.autofocus) {
                this._focusInput();
            }
        }
        const height = this.isFolded() ? this.HEIGHT_FOLDED : this.HEIGHT_OPEN;
        this.$el.css({ height });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set the focus on the composer of the thread window. This operation is
     * ignored in mobile context.
     *
     * @private
     * Set the focus on the input of the window
     */
    _focusInput() {
        if (
            config.device.touch &&
            config.device.size_class <= config.device.SIZES.SM
        ) {
            return;
        }
        this.$input.focus();
    },
    /**
     * Returns the options used by the rendering of the window's header
     *
     * @private
     * @returns {Object}
     */
    _getHeaderRenderingOptions() {
        return {
            status: this.getThreadStatus(),
            thread: this.getThread(),
            title: this.getTitle(),
            unreadCounter: this.getUnreadCounter(),
            widget: this,
        };
    },
    /**
     * Get the ID of the related thread.
     * If this window is not related to a thread, it means this is the "blank"
     * thread window, therefore it returns "_blank" as its ID.
     *
     * @private
     * @returns {integer|string} the threadID, or '_blank' for the window that
     *   is not related to any thread.
     */
    _getThreadID() {
        if (!this.hasThread()) {
            return '_blank';
        }
        return this._thread.getID();
    },
    /**
     * Tells whether there is focus on this thread. Note that a thread that has
     * the focus means the input has focus.
     *
     * @private
     * @returns {boolean}
     */
    _hasFocus() {
        return this.$input.is(':focus');
    },
    /**
     * Post a message on this thread window, and auto-scroll to the bottom of
     * the thread.
     *
     * @private
     * @param {Object} messageData
     */
    _postMessage(messageData) {
        this.trigger_up('post_message_chat_window', { messageData });
        if (!this.hasThread()) {
            return;
        }
        this._thread.postMessage(messageData)
            .then(() => {
                this._threadWidget.scrollToBottom();
            });
    },
    /**
     * Update the fold state of the thread.
     *
     * This function is called when toggling the fold state of this window.
     * If there is no thread linked to this window, it means this is the
     * "blank" thread window, therefore we use the internal state 'folded'
     *
     * @private
     * @param {boolean} folded
     */
    _updateThreadFoldState(folded) {
        if (this.hasThread()) {
            this._thread.fold(folded);
        } else {
            this._folded = folded;
            this.updateVisualFoldState();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Close the thread window.
     * Mark the thread as read if the thread window was open.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (
            this.hasThread() &&
            this._thread.getUnreadCounter() > 0 &&
            !this.isFolded()
        ) {
            this._thread.markAsRead();
        }
        this.close();
    },
    /**
     * Fold/unfold the thread window.
     * Also mark the thread as read.
     *
     * @private
     */
    _onClickFold() {
        if (!config.device.isMobile) {
            this.toggleFold();
        }
    },
    /**
     * Called when the composer is clicked -> forces focus on input even if
     * jquery's blockUI is enabled.
     *
     * @private
     * @param {Event} ev
     */
    _onComposerClick(ev) {
        if ($(ev.target).closest('a, button').length) {
            return;
        }
        this._focusInput();
    },
    /**
     * @private
     */
    _onDocumentViewerClose() {
        this._focusInput();
    },
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
    /**
     * Called when typing something on the composer of this thread window.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (ev.which === 13) {
            const content = _.str.trim(this.$input.val());
            const messageData = {
                content,
                attachment_ids: [],
                partner_ids: [],
            };
            this.$input.val('');
            if (content) {
                this._postMessage(messageData);
            }
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeypress(ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
    },
    /**
     * @private
     */
    _onScroll() {
        if (this.hasThread() && this.isAtBottom()) {
            this._thread.markAsRead();
        }
    },
    /**
     * When a thread window is clicked on, we want to give the focus to the main
     * input. An exception is made when the user is selecting something.
     *
     * @private
     */
    _onThreadWindowClicked() {
        const selectObj = window.getSelection();
        if (selectObj.anchorOffset === selectObj.focusOffset) {
            this.$input.focus();
        }
    },
});

export default PublicLivechatWindow;
