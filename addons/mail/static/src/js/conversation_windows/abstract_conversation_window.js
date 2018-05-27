odoo.define('mail.widget.AbstractConversationWindow', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var HEIGHT_OPEN = '400px';
var HEIGHT_FOLDED = '34px';

var AbstractConversationWindow = Widget.extend({
    template: 'mail.AbstractConversationWindow',
    custom_events: {
        escape_pressed: '_onEscapePressed'
    },
    events: {
        'click .o_conversation_window_close': '_onClickClose',
        'click .o_conversation_window_title': '_onClickFold',
        'click .o_conversation_composer': '_onComposerClick',
        'click .o_mail_thread': '_onConversationWindowClicked',
        'keydown .o_conversation_composer': '_onKeydown',
        'keypress .o_conversation_composer': '_onKeypress',
    },
    /**
     * Children of this class must make use of `conversation`,
     * which is an object that represent the conversation that
     * is linked to this conversation window.
     *
     * @abstract
     * @param {Widget} parent
     * @param {Object} conversation
     * @param {Object} options
     */
    init: function (parent, conversation, options) {
        this._super(parent);

        this.options = _.defaults(options || {}, {
            autofocus: true,
            displayStar: true,
            displayReplyIcon: false,
            displayEmail: false,
            placeholder: _t("Say something"),
        });

        this._hidden = false;
        this._status = this.options.status;
    },
    start: function () {
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_conversation_window_header');

        this.threadWidget = new ThreadWidget(this, {
            threadID: this._getConversationID(),
            displayMarkAsRead: false,
            displayStar: this.options.displayStar,
        });
        this.threadWidget.on('toggle_star_status', null, this.trigger.bind(this, 'toggle_star_status'));
        this.threadWidget.on('redirect_to_channel', null, this.trigger.bind(this, 'redirect_to_channel'));
        this.threadWidget.on('redirect', null, this.trigger.bind(this, 'redirect'));

        if (this.isFolded()) {
            this.$el.css('height', HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this._focusInput();
        }
        if (!config.device.isMobile) {
            this.$el.css('margin-right', $.position.scrollbarWidth());
        }
        var def = this.threadWidget.replace(this.$('.o_chat_content'));
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
     * @return {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * @abstract
     * @returns {string}
     */
    getTitle: function () {},
    /**
     * @abstract
     * @returns {integer}
     */
    getUnreadCounter: function () {},
    /**
     * States whether this conversation window is related to a conversation or not.
     *
     * This is useful in order to provide specific behaviour for conversation windows
     * without any conversation, e.g. let them open a conversation from this
     * "new conversation" window
     *
     * @abstract
     * @returns {boolean}
     */
    hasConversation: function () {},
    /**
     * @abstract
     * @returns {boolean}
     */
    isFolded: function () {},
    /**
     * @returns {boolean}
     */
    isMobile: function () {
        return config.device.isMobile;
    },
    /**
     * @returns {boolean}
     */
    isHidden: function () {
        return this._hidden;
    },
    /**
     * @param {Object[]} messages
     */
    render: function (messages) {
        this._renderHeader();
        this.threadWidget.render(messages, { displayLoadMore: false });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _animateFold: function () {
        this.$el.animate({
            height: this.isFolded() ? HEIGHT_FOLDED : HEIGHT_OPEN
        }, 200);
    },
    /**
     * @private
     * Set the focus on the input of the conversation window
     */
    _focusInput: function () {
        if (config.device.touch && config.device.size_class <= config.device.SIZES.SM) {
            return;
        }
        this.$input.focus();
    },
    /**
     * Get the ID of the related conversation
     * If there is no conversation related to this conversation window,
     * returns 0;
     *
     * @abstract
     * @return {integer}
     */
    _getConversationID: function () {},
    /**
     * Update the fold state of the related conversation.
     * This function is called when toggling the fold state of this conversation window
     *
     * @abstract
     * @private
     * @param {boolean} folded
     */
    _updateConversationFoldState: function (folded) {},
    /**
     * @private
     */
    _renderHeader: function () {
        this.$header.html(QWeb.render('mail.AbstractConversationWindowHeaderContent', {
            status: this._status,
            title: this.getTitle(),
            unreadCounter: this.getUnreadCounter(),
            widget: this,
        }));
    },
    /**
     * @private
     * @param {boolean} folded
     */
    _toggleFold: function (folded) {
        if (!_.isBoolean(folded)) {
            folded = !this.isFolded();
        }
        this._updateConversationFoldState(folded);
        if (!this.isFolded()) {
            this.threadWidget.scrollToBottom();
            this._focusInput();
        }
        this._animateFold();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.trigger('close_chat_session', this._getConversationID());
    },
    /**
     * @private
     */
    _onClickFold: function () {
        if (!config.device.isMobile) {
            this._toggleFold();
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
     * When a conversation window is clicked on, we want to give the focus to the main
     * input. An exception is made when the user is selecting something.
     *
     * @private
     */
    _onConversationWindowClicked: function () {
        var selectObj = window.getSelection();
        if (selectObj.anchorOffset === selectObj.focusOffset) {
            this.$input.focus();
        }
    },
    /**
     * @private
     */
    _onEscapePressed: function () {
        if (!this.isFolded()) {
            this.trigger('close_chat_session', this._getConversationID());
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (ev.which === 13) {
            var content = _.str.trim(this.$input.val());
            var message = {
                content: content,
                attachment_ids: [],
                partner_ids: [],
            };
            this.$input.val('');
            if (content) {
                this.trigger('post_message', message, {
                    channelID: this._getConversationID(),
                });
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
});

return AbstractConversationWindow;

});
