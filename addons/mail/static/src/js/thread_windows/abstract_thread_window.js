odoo.define('mail.AbstractThreadWindow', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * This is an abstract widget for rendering thread windows.
 *
 * It contains logic that are shared between mail.ThreadWindow and
 * im_livechat.WebsiteLivechatWindow.
 *
 * The reason for having two different implementation of thread windows is
 * that mail.ThreadWindow makes use of mail.Manager, which is used in the
 * backend, while im_livechat.WebsiteLivechatWindow must work without this
 * mail service.
 */
var AbstractThreadWindow = Widget.extend({
    template: 'mail.AbstractThreadWindow',
    custom_events: {
        escape_pressed: '_onEscapePressed',
        document_viewer_closed: '_onDocumentViewerClose',
    },
    events: {
        'click .o_thread_window_close': '_onClickClose',
        'click .o_thread_window_title': '_onClickFold',
        'click .o_composer_text_field': '_onComposerClick',
        'click .o_mail_thread': '_onThreadWindowClicked',
        'keydown .o_composer_text_field': '_onKeydown',
        'keypress .o_composer_text_field': '_onKeypress',
    },
    FOLD_ANIMATION_DURATION: 200, // duration in ms for (un)fold transition
    HEIGHT_OPEN: '400px', // height in px of thread window when open
    HEIGHT_FOLDED: '34px', // height, in px, of thread window when folded
    /**
     * Children of this class must make use of `thread`, which is an object that
     * represent the thread that is linked to this thread window.
     *
     * If no thread is provided, this will represent the "blank" thread window.
     *
     * @abstract
     * @param {Widget} parent
     * @param {mail.model.AbstractThread} [thread=null] the thread that this
     *   thread window is linked to. If not set, it is the "blank" thread
     *   window.
     * @param {Object} [options={}]
     * @param {mail.model.AbstractThread} [options.thread]
     */
    init: function (parent, thread, options) {
        this._super(parent);

        this.options = _.defaults(options || {}, {
            autofocus: true,
            displayStars: true,
            displayReplyIcons: false,
            displayEmailIcons: false,
            placeholder: _t("Say something"),
        });

        this._hidden = false;
        this._thread = thread || null;

        this._debouncedOnScroll = _.debounce(this._onScroll.bind(this), 100);

        if (!this.hasThread()) {
            // internal fold state of thread window without any thread
            this._folded = false;
        }
    },
    start: function () {
        var self = this;
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_thread_window_header');

        this._threadWidget = new ThreadWidget(this, {
            displayMarkAsRead: false,
            displayStars: this.options.displayStars,
        });

        if (this.isFolded()) {
            this.$el.css('height', this.HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this._focusInput();
        }
        if (!config.device.isMobile) {
            var margin_dir = _t.database.parameters.direction === "rtl" ? "margin-left" : "margin-right";
            this.$el.css(margin_dir, $.position.scrollbarWidth());
        }
        var def = this._threadWidget.replace(this.$('.o_thread_window_content')).then(function () {
            self._threadWidget.$el.on('scroll', self, self._debouncedOnScroll);
        });
        return $.when(this._super(), def);
    },
    /**
     * @override
     */
    do_hide: function () {
        this._hidden = true;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_show: function () {
        this._hidden = false;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_toggle: function (display) {
        this._hidden = _.isBoolean(display) ? !display : !this._hidden;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close this window
     *
     * @abstract
     */
    close: function () {},
    /**
     * Get the ID of the thread window, which is equivalent to the ID of the
     * thread related to this window
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._getThreadID();
    },
    /**
     * Get the status of the thread, such as the im status of a DM chat
     * ('online', 'offline', etc.). If this window has no thread, returns
     * `undefined`.
     *
     * @returns {string|undefined}
     */
    getThreadStatus: function () {
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
    getTitle: function () {
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
    getUnreadCounter: function () {
        if (!this.hasThread()) {
            return 0;
        }
        return this._thread.getUnreadCounter();
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
    hasThread: function () {
        return !! this._thread;
    },
    /**
     * Tells whether the bottom of the thread in the thread window is visible
     * or not.
     *
     * @returns {boolean}
     */
    isAtBottom: function () {
        return this._threadWidget.isAtBottom();
    },
    /**
     * State whether the related thread is folded or not. If there are no
     * thread related to this window, it means this is the "blank" thread
     * window, therefore we use the internal folded state.
     *
     * @returns {boolean}
     */
    isFolded: function () {
        if (!this.hasThread()) {
            return this._folded;
        }
        return this._thread.isFolded();
    },
    /**
     * States whether the current environment is in mobile or not. This is
     * useful in order to customize the template rendering for mobile view.
     *
     * @returns {boolean}
     */
    isMobile: function () {
        return config.device.isMobile;
    },
    /**
     * States whether the thread window is hidden or not.
     *
     * @returns {boolean}
     */
    isHidden: function () {
        return this._hidden;
    },
    /**
     * States whether the input of the thread window should be displayed or not.
     * By default, any thread window with a thread needs a composer.
     *
     * @returns {boolean}
     */
    needsComposer: function () {
        return this.hasThread();
    },
    /**
     * Render the thread window
     */
    render: function () {
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
    renderHeader: function () {
        var options = this._getHeaderRenderingOptions();
        this.$header.html(
            QWeb.render('mail.AbstractThreadWindow.HeaderContent', options));
    },
    /**
     * Render the 'is typing...' notification bar text on the thread in this
     * thread window. This is called when there is a change in the list of users
     * currently typing something on this thread.
     */
    renderTypingNotificationBar: function () {
        this._threadWidget.renderTypingNotificationBar(this._thread);
    },
    /**
     * Scroll to the bottom of the thread in the thread window
     */
    scrollToBottom: function () {
        this._threadWidget.scrollToBottom();
    },
    /**
     * Toggle the fold state of this thread window. Also update the fold state
     * of the thread model. If the boolean parameter `folded` is provided, it
     * folds/unfolds the window when it is set/unset.
     *
     * @param {boolean} [folded] if not a boolean, toggle the fold state.
     *   Otherwise, fold/unfold the window if set/unset.
     */
    toggleFold: function (folded) {
        if (!_.isBoolean(folded)) {
            folded = !this.isFolded();
        }
        this._updateThreadFoldState(folded);
    },
    /**
     * Update the visual state of the window so that it matched the internal
     * fold state. This is useful in case the related thread has its fold state
     * that has been changed.
     */
    updateVisualFoldState: function () {
        if (!this.isFolded()) {
            this._threadWidget.scrollToBottom();
            if (this.options.autofocus) {
                this._focusInput();
            }
        }
        this._animateFold();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when there is a change of the fold state of the thread window.
     * This method animates the change of fold state of this thread window.
     *
     * @private
     */
    _animateFold: function () {
        this.$el.animate({
            height: this.isFolded() ? this.HEIGHT_FOLDED : this.HEIGHT_OPEN
        }, this.FOLD_ANIMATION_DURATION);
    },
    /**
     * Set the focus on the composer of the thread window. This operation is
     * ignored in mobile context.
     *
     * @private
     * Set the focus on the input of the window
     */
    _focusInput: function () {
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
    _getHeaderRenderingOptions: function () {
        return {
            status: this.getThreadStatus(),
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
    _getThreadID: function () {
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
    _hasFocus: function () {
        return this.$input.is(':focus');
    },
    /**
     * Post a message on this thread window, and auto-scroll to the bottom of
     * the thread.
     *
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        var self = this;
        if (!this.hasThread()) {
            return;
        }
        this._thread.postMessage(messageData)
            .then(function () {
                self._threadWidget.scrollToBottom();
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
    _updateThreadFoldState: function (folded) {
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
    _onClickClose: function (ev) {
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
    _onClickFold: function () {
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
    _onComposerClick: function (ev) {
        if ($(ev.target).closest('a, button').length) {
            return;
        }
        this._focusInput();
    },
    /**
     * @private
     */
    _onDocumentViewerClose: function () {
        this._focusInput();
    },
    /**
     * @private
     */
    _onEscapePressed: function () {
        if (!this.isFolded()) {
            this.close();
        }
    },
    /**
     * Called when typing something on the composer of this thread window.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (ev.which === 13) {
            var content = _.str.trim(this.$input.val());
            var messageData = {
                content: content,
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
    _onKeypress: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
    },
    /**
     * @private
     */
    _onScroll: function () {
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
    _onThreadWindowClicked: function () {
        var selectObj = window.getSelection();
        if (selectObj.anchorOffset === selectObj.focusOffset) {
            this.$input.focus();
        }
    },
});

return AbstractThreadWindow;

});
