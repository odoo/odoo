odoo.define('mail.ThreadWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');
var BasicComposer = require('mail.composer.Basic');
var ExtendedComposer = require('mail.composer.Extended');

var config = require('web.config');
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
    custom_events: AbstractThreadWindow.prototype.custom_events,
    events: _.extend({}, AbstractThreadWindow.prototype.events, {
        'click .o_mail_thread': '_onThreadWindowFocus',
        'click .o_thread_composer': '_onThreadWindowFocus',
        'click .o_thread_window_expand': '_onClickExpand',
    }),
    /**
     * Version of thread window that supports {mail.model.Thread}
     *
     * @override
     * @param {mail.Manager} parent
     * @param {mail.model.Thread} [thread = null] if not set, this is a "blank"
     *   thread window. It lets us open a DM chat by providing the name of a
     *   user.
     * @param {Object} [options={}]
     * @param {boolean} [options.passively=false]
     */
    init: function (parent, thread, options) {
        this._super.apply(this, arguments);

        // don't automatically mark unread messages as seen when at the bottom
        // of the thread
        this._passive = this.options.passively || false;

        if (!this.hasThread()) {
            // remembered partner ID of "blank" thread window in order to be
            // replaced with newly opened DM chat window
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
        } else if (this.needsComposer()) {
            var composer;
            var composerParams = {
                mentionPartnersRestricted: this._thread.getType() !== 'document_thread',
                thread: this._thread,
            };
            if (
                config.device.isMobile &&
                this._thread.isMassMailing()
            ) {
                composer = new ExtendedComposer(this, composerParams);
            } else {
                composer = new BasicComposer(this, _.extend({ isMini: true }, composerParams));
            }
            composer.on('post_message', this, this._postMessage);
            composer.once('input_focused', this, function () {
                var commands = this._thread.getCommands();
                var partners = this._thread.getMentionPartnerSuggestions();
                composer.mentionSetCommands(commands);
                composer.mentionSetPrefetchedPartners(partners);
            });
            composerDef = composer.replace(this.$('.o_thread_composer'));
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
        if (this.hasThread()) {
            this._thread.close();
        } else {
            this.trigger_up('close_blank_thread_window');
        }
    },
    /**
     * Set the focus on the input of this thread window
     */
    focusInput: function () {
        this._focusInput();
    },
    /**
     * Overrides so that if this thread window is not linked to any thread
     * (= "blank" thread window), displays "New message" as its title.
     *
     * @override
     * @returns {string}
     */
    getTitle: function () {
        if (!this.hasThread()) {
            return _t("New message");
        }
        return this._super.apply(this, arguments);
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
     * Update this thread window
     *
     * @param {Object} options
     * @param {boolean} [options.keepBottom=false] if set, this thread window
     *   should scroll to the bottom if it was at the bottom before update
     * @param {boolean} [options.passively=false] if set, this thread window
     *   becomes passive, so that it is marked as read only when the focus is
     *   on it. Ignore this option if the focus is already on the thread window.
     */
    update: function (options) {
        var self = this;
        if (options.passively && !this._hasFocus()) {
            this._setPassive();
        }
        var bottomVisible = !this.isFolded() &&
                            !this.isHidden() &&
                            this.isAtBottom();
        if (bottomVisible && !this.isPassive()) {
            this._thread.markAsRead();
        }
        this._thread.fetchMessages().then(function () {
            self.render();
            if (bottomVisible && options.keepBottom) {
                self.scrollToBottom();
            }
        });
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
     * Listen on thread widget events
     *
     * @private
     */
    _listenThreadWidget: function () {
        this._threadWidget
            .on('redirect', this, this._onRedirect)
            .on('redirect_to_channel', this, this._onRedirectToChannel)
            .on('toggle_star_status', this, this._onToggleStarStatus);
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
     * Set the thread window in passive mode, so that new received message will
     * keep the thread window as unread until there is focus on the thread
     * window.
     *
     * @private
     */
    _setPassive: function () {
        this._passive = true;
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
                    // with new DM chat window
                    var partnerID = ui.item.id;
                    self.directPartnerID = partnerID;
                    self.call('mail_service', 'openDMChatWindowFromBlankThreadWindow', partnerID);
                },
            })
            .focus();
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
        if (this.hasThread() && this._thread.getType() === 'document_thread') {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: this._thread.getDocumentModel(),
                views: [[false, 'form']],
                res_id: this._thread.getDocumentID(),
            });
        } else {
            this.do_action('mail.action_discuss', {
                clear_breadcrumbs: false,
                active_id: this.hasThread() ? this._getThreadID() : undefined,
                on_reverse_breadcrumb: function () {
                    var mailBus = self.call('mail_service', 'getMailBus');
                    if (mailBus) {
                        mailBus.trigger('discuss_open', false);
                    }
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
     * Override it so that passive thread windows do not mark thread as read
     * on scroll
     *
     * @override
     * @private
     */
    _onScroll: function () {
        if (this.isPassive()) {
            return;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Called when focusing the thread window (click on thread or composer)
     *
     * @private
     */
    _onThreadWindowFocus: function () {
        if (this.isPassive()) {
            this.removePassive();
            this._thread.markAsRead();
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
