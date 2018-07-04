odoo.define('mail.ThreadWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');
var BasicComposer = require('mail.composer.Basic');

var core = require('web.core');

var _t = core._t;

/**
 * This is the main widget for rendering small windows for mail.model.Thread.
 * Almost all instances of this class are linked to a thread. The sole
 * exception is the "blank" thread window. This window let us open another
 * thread window, using this "blank" thread window.
 */
var ThreadWindow = AbstractThreadWindow.extend({
    template: 'mail.ThreadWindow',
    events: _.extend({}, AbstractThreadWindow.prototype.events, {
        'click .o_thread_window_expand': '_onClickExpand',
    }),
    /**
     * Version of thread window that supports {mail.model.Thread}
     *
     * @override
     * @param {mail.Manager} parent
     * @param {mail.model.Thread} [thread = null] if not set, this is a "blank"
     *   thread window. It lets us open a DM by providing the name of a chat.
     * @param {Object} [options={}]
     * @param {boolean} [options.passively=false]
     */
    init: function (parent, thread, options) {
        this._super.apply(this, arguments);

        // don't automatically mark unread messages as seen when at the bottom
        // of the thread
        this._passive = this.options.passively;
        this._thread = thread || null;

        if (!this.hasThread()) {
            // internal fold state of thread window without any thread
            this._folded = false;
            // remembered partner ID of "blank" thread window in order to be
            // replaced with newly opened DM window
            this.directPartnerID = null;
        }
    },

    /**
     * @override
     */
    start: function () {
        var self = this;

        var superDef = this._super().then(this._listenThreadWidget.bind(this));

        var composerDef;
        if (!this.hasThread()) {
            this._startWithoutThread();
        } else if (this._needsComposer()) {
            var basicComposer = new BasicComposer(this, {
                mentionPartnersRestricted: this._thread.getType() !== 'document_thread',
                isMini: true
            });
            basicComposer.on('post_message', this, this._postMessage);
            basicComposer.once('input_focused', this, function () {
                var commands = this._thread.getCommands();
                var partners = this._thread.getMentionPartnerSuggestions();
                basicComposer.mentionSetCommands(commands);
                basicComposer.mentionSetPrefetchedPartners(partners);
            });
            composerDef = basicComposer.replace(this.$('.o_thread_composer'));
            composerDef.then(function () {
                self.$input = self.$('.o_composer_text_field');
            });
        }

        return $.when(superDef, composerDef);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        if (this._hasThread()) {
            this._thread.close();
        }
    },
    /**
     * Set the focus on the input of this thread window
     */
    focusInput: function () {
        this._focusInput();
    },
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
     * Get the status of the thread. If this window has no thread, returns
     * 'undefined'
     *
     * @override
     * @returns {string|undefined}
     */
    getStatus: function () {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread.getStatus();
    },
    /**
     * Get the title of the thread window, which is equivalent to the name of
     * related thread, prefixed with "#" if this is a chat (i.e. DM, backend
     * livechat).
     *
     * If there is no thread linked to this thread window, display title of
     * "blank" thread window.
     *
     * @override
     * @returns {string}
     */
    getTitle: function () {
        if (!this.hasThread()) {
            return _t("New message");
        }
        return this._thread.getTitle();
    },
    /**
     * Get the unread counter of the related thread. If there are no thread
     * linked to this window, returns 0.
     *
     * @override
     * @returns {integer}
     */
    getUnreadCounter: function () {
        if (!this.hasThread()) {
            return 0;
        }
        return this._thread.getUnreadCounter();
    },
    /**
     * @override
     * @returns {boolean}
     */
    hasThread: function () {
        return !!this._thread;
    },
    /**
     * State whether the related thread is folded or not. If there are no
     * thread related to this window, it means this is the "blank" thread
     * window, therefore we use the internal folded state.
     *
     * @override
     * @returns {boolean}
     */
    isFolded: function () {
        if (!this.hasThread()) {
            return this._folded;
        }
        return this._thread.isFolded();
    },
    /**
     * Tell whether the thread window is passive or not. A passive thread window
     * does not auto-mark the thread as read when scrolling at the bottom.
     *
     * @returns {boolean}
     */
    isPassive: function () {
        return this._passive;
    },
    /**
     * Turn the thread window in active mode, so that when the bottom of the
     * thread is visible, it is automatically marked as read.
     */
    removePassive: function () {
        this._passive = false;
    },
    /**
     * Update the header of this thread window
     * This is useful when some information on the header have be updated
     * such as the status or the title of the thread that have changed.
     */
    updateHeader: function () {
        this._renderHeader();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getHeaderRenderingOptions: function () {
        var options = this._super.apply(this, arguments);
        if (this._thread.getType() === 'document_thread') {
            options.expandTitle = _t("Open document");
        } else {
            options.expandTitle = _t("Open in Discuss");
        }
        return options;
    },
    /**
     * States whether the window is linked to a thread or not
     *
     * Useful to detect whether this is the "blank" thread window or not.
     *
     * @private
     * @returns {boolean}
     */
    _hasThread: function () {
        return !!this._thread;
    },
    /**
     * Listen on thread widget events
     *
     * @private
     */
    _listenThreadWidget: function () {
        this.threadWidget
            .on('redirect', this, this._onRedirect)
            .on('redirect_to_channel', this, this._onRedirectToChannel)
            .on('toggle_star_status', this, this._onToggleStarStatus);
    },
    /**
     * States whether the input of the thread window should be displayed or not.
     * This is based on the type of the thread:
     *
     * Do not display the input in the following cases:
     *
     *      - no thread related to this window
     *      - window of a mailbox (temp: let us have mailboxes in window mode)
     *      - window of a thread with mass mailing
     *
     * Any other threads show the input in the window.
     *
     * @private
     * @returns {boolean}
     */
    _needsComposer: function () {
        return this.hasThread() &&
                (this._thread.getType() !== 'mailbox') &&
                !this._thread.isMassMailing();
    },
    /**
     * Open this thread window.
     * This private method exists only for the purpose of providing a callback
     * function on redirect to a partner.
     *
     * @private
     */
    _open: function () {
        this.call('mail_service', 'openThreadWindow', this.getID());
    },
    /**
     * Post a message in the thread related to this window.
     * If this window has no thread, do nothing
     *
     * @override
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        var self = this;
        if (!this._hasThread()) {
            return;
        }
        this._thread.postMessage(messageData)
            .then(function () {
                self.threadWidget.scrollToBottom();
            });
    },
    /**
     * @private
     */
    _startWithoutThread: function () {
        var self = this;
        this.$el.addClass('o_thread_less');
        this.$('.o_thread_search_input input')
            .autocomplete({
                source: function (request, response) {
                    self.call('mail_service', 'searchPartner', request.term, 10)
                        .done(response);
                },
                select: function (event, ui) {
                    // remember partner ID so that we can replace this window
                    // with new DM window
                    var partnerID = ui.item.id;
                    self.directPartnerID = partnerID;
                    self.call('mail_service', 'openDmWindow', partnerID);
                },
            })
            .focus();
    },
    /**
     * Update the fold state of the thread
     * If there is no thread linked to this window, it means this is the
     * "blank" thread window, therefore we use the internal state 'folded'
     *
     * @override
     * @private
     * @param {boolean} folded
     */
    _updateThreadFoldState: function (folded) {
        if (this.hasThread()) {
            this._thread.fold(folded);
        } else {
            this._folded = folded;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Expand the thread, which will open the thread in discuss.
     *
     * If there is no thread linked to this window, it means this is the "blank"
     * thread window, therefore it opens discuss with the default thread (which
     * should be the mailbox 'inbox')
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickExpand: _.debounce(function (ev) {
        var self = this;
        ev.preventDefault();
        if (this._thread.getType() === 'document_thread') {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: this._thread.getDocumentModel(),
                views: [[false, 'form']],
                res_id: this._thread.getDocumentID(),
            });
        } else {
            this.do_action('mail.mail_channel_action_client_chat', {
                clear_breadcrumbs: false,
                active_id: this.hasThread() ? this._getThreadID() : undefined,
                on_reverse_breadcrumb: function () {
                    self.call('mail_service', 'getMailBus')
                        .trigger('discuss_open', false);
                },
            });
        }
    }, 1000, true),
    /**
     * @override
     * @private
     * @param {KeyboardEvent} ev
     *
     * Override _onKeydown to only prevent jquery's blockUI to cancel event,
     * but without sending the message on ENTER keydown as this is handled by
     * the BasicComposer
     */
    _onKeydown: function (ev) {
        ev.stopPropagation();
    },
    /**
     * callback function receives the threadID linked to resModel and resID
     * Note: this callback function is only called for 'res.partner'
     *
     * @private
     * @param {string} resModel
     * @param {integer} resID
     */
    _onRedirect: function (resModel, resID) {
        var callback = this._open.bind(this);
        this.call('mail_service', 'redirect', resModel, resID, callback);
    },
    /**
     * @private
     * @param {integer} channelID
     */
    _onRedirectToChannel: function (channelID) {
        var thread = this.call('mail_service', 'getThread', channelID);
        if (!thread) {
            this.call('mail_service', 'joinChannel', channelID)
                .then(function (channel) {
                    channel.detach();
                });
        } else {
            this.toggleFold(false);
        }
    },
    /**
     * @private
     * @param {integer} messageID
     */
    _onToggleStarStatus: function (messageID) {
        var message = this.call('mail_service', 'getMessage', messageID);
        message.toggleStarStatus();
    },

});

return ThreadWindow;

});
