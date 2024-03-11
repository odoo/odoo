/** @odoo-module **/

import config from 'web.config';
import { _t, qweb } from 'web.core';
import Widget from 'web.Widget';

import {unaccent} from 'web.utils';
import {setCookie} from 'web.utils.cookies';

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
        'click .o_thread_window_header': '_onClickFold',
        'click .o_composer_text_field': '_onComposerClick',
        'click .o_mail_thread': '_onThreadWindowClicked',
        'keydown .o_composer_text_field': '_onKeydown',
        'keypress .o_composer_text_field': '_onKeypress',
        'input .o_composer_text_field': '_onInput',
    },
    /**
     * @param {Widget} parent
     * @param {Messaging} messaging
     * @param {@im_livechat/legacy/models/public_livechat} thread
     */
    init(parent, messaging, thread) {
        this._super(parent);
        this.messaging = messaging;

        this._debouncedOnScroll = _.debounce(this._onScroll.bind(this), 100);
    },
    /**
     * @override
     * @return {Promise}
     */
    async start() {
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_thread_window_header');

        // animate the (un)folding of thread windows
        this.$el.css({ transition: 'height ' + this.FOLD_ANIMATION_DURATION + 'ms linear' });
        if (this.messaging.publicLivechatGlobal.publicLivechat.isFolded) {
            this.$el.css('height', this.HEIGHT_FOLDED);
        } else {
            this._focusInput();
        }
        const def = this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.replace(this.$('.o_thread_window_content')).then(() => {
            this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.$el.on('scroll', this, this._debouncedOnScroll);
        });
        await Promise.all([this._super(), def]);
        if (this.messaging.publicLivechatGlobal.livechatButtonView.headerBackgroundColor) {
            this.$('.o_thread_window_header').css('background-color', this.messaging.publicLivechatGlobal.livechatButtonView.headerBackgroundColor);
        }
        if (this.messaging.publicLivechatGlobal.livechatButtonView.titleColor) {
            this.$('.o_thread_window_header').css('color', this.messaging.publicLivechatGlobal.livechatButtonView.titleColor);
        }
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close() {
        const isComposerDisabled = this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_thread_composer input').prop('disabled');
        const shouldAskFeedback = !isComposerDisabled && this.messaging.publicLivechatGlobal.messages.find(function (message) {
            return message.id !== '_welcome';
        });
        if (shouldAskFeedback) {
            this.messaging.publicLivechatGlobal.chatWindow.widget.toggleFold(false);
            this.messaging.publicLivechatGlobal.livechatButtonView.askFeedback();
        } else {
            this.messaging.publicLivechatGlobal.livechatButtonView.closeChat();
        }
        this.messaging.publicLivechatGlobal.leaveSession();
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
     * Render the thread window
     */
    render() {
        this.renderHeader();
        this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.render({ displayLoadMore: false });
    },
    /**
     * Render the header of this thread window.
     * This is useful when some information on the header have be updated such
     * as the status or the title of the thread that have changed.
     *
     * @private
     */
    renderHeader() {
        this.$header.html(qweb.render('im_livechat.legacy.PublicLivechatWindow.HeaderContent', { widget: this }));
    },

    /**
     * Render the chat window itself.
     */
    renderChatWindow() {
        this.renderElement();
        this.adjustPosition();
    },

    /**
     * Compute position of this chat window and apply corresponding styles to
     * the underlying widget.
     */
    adjustPosition() {
        const cssProps = { bottom: 0 };
        cssProps[this.messaging.locale.textDirection === 'rtl' ? 'left' : 'right'] = 0;
        if (!config.device.isMobile) {
            const margin_dir = _t.database.parameters.direction === "rtl" ? "margin-left" : "margin-right";
            cssProps[margin_dir] = $.position.scrollbarWidth();
        }
        this.$el.css(cssProps);
    },

    /**
     * Replace the thread content with provided new content
     *
     * @param {$.Element} $element
     */
    replaceContentWith($element) {
        $element.replace(this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.$el);
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
            folded = !this.messaging.publicLivechatGlobal.publicLivechat.isFolded;
        }
        this.messaging.publicLivechatGlobal.publicLivechat.update({ isFolded: folded });
        if (this.messaging.publicLivechatGlobal.publicLivechat.operator) {
            setCookie('im_livechat_session', unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.widget.toData()), true), 60 * 60, 'required');
        }
        this.updateVisualFoldState();
    },
    /**
     * Update the visual state of the window so that it matched the internal
     * fold state. This is useful in case the related thread has its fold state
     * that has been changed.
     */
    updateVisualFoldState() {
        if (!this.messaging.publicLivechatGlobal.publicLivechat.isFolded) {
            this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
            this._focusInput();
        }
        const height = this.messaging.publicLivechatGlobal.publicLivechat.isFolded ? this.HEIGHT_FOLDED : this.HEIGHT_OPEN;
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
    async _postMessage(messageData) {
        try {
            await this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage(messageData);
        } catch (_err) {
            await this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage(messageData); // try again just in case
        }
        if (!this.messaging.publicLivechatGlobal.publicLivechat.operator) {
            return;
        }
        this.messaging.publicLivechatGlobal.publicLivechat.widget.postMessage(messageData)
            .then(() => {
                this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
            });
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
            this.messaging.publicLivechatGlobal.publicLivechat.unreadCounter > 0 &&
            !this.messaging.publicLivechatGlobal.publicLivechat.isFolded
        ) {
            this.messaging.publicLivechatGlobal.publicLivechat.widget.markAsRead();
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
     * Called when the input in the composer changes
     *
     * @private
     */
    _onInput() {
        const isTyping = this.$input.val().length > 0;
        this.messaging.publicLivechatGlobal.publicLivechat.widget.setMyselfTyping({ typing: isTyping });
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
        if (
            !this.messaging.exists() ||
            !this.messaging.publicLivechatGlobal ||
            !this.messaging.publicLivechatGlobal.chatWindow
        ) {
            return;
        }
        if (this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom()) {
            this.messaging.publicLivechatGlobal.publicLivechat.widget.markAsRead();
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
