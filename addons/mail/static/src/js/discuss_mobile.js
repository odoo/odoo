odoo.define('mail.DiscussMobile', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

var config = require('web.config');
var core = require('web.core');

var QWeb = core.qweb;

if (!config.device.isMobile) {
    return;
}

/**
 * Overrides Discuss module in mobile
 */
Discuss.include({
    template: 'mail.discuss_mobile',
    events: _.extend(Discuss.prototype.events, {
        'click .o_mail_mobile_tab': '_onMobileTabClicked',
        'click .o_mailbox_inbox_item': '_onMobileInboxButtonClicked',
        'click .o_mail_preview': '_onMobileThreadClicked',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._currentState = this._defaultThreadID;
    },
    /**
     * @override
     */
    start: function () {
        this._$mainContent = this.$('.o_mail_discuss_content');
        return this._super.apply(this, arguments)
            .then(this._updateControlPanel.bind(this));
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        if (this._thread && this._isInInboxTab()) {
            this._threadWidget.scrollToPosition(this._threadsScrolltop[this._thread.getID()]);
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        if (this._isInInboxTab()) {
            this._threadsScrolltop[this._thread.getID()] = this._threadWidget.getScrolltop();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Boolean} true iff we currently are in the Inbox tab
     */
    _isInInboxTab: function () {
        return _.contains(['mailbox_inbox', 'mailbox_starred'], this._currentState);
    },
    /**
     * @override
     * @private
     */
    _renderButtons: function () {
        var self = this;
        this._super.apply(this, arguments);
        _.each(['dm_chat', 'public', 'private'], function (type) {
            var selector = '.o_mail_discuss_button_' + type;
            self.$buttons.on('click', selector, self._onAddThread.bind(self));
        });
    },
    /**
     * Overrides to only store the thread state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed thread
     *
     * @override
     * @private
     */
    _restoreThreadState: function () {
        if (this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is selected
     *
     * @override
     * @private
     */
    _selectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').addClass('o_hidden');
    },
    /**
     * @override
     * @private
     */
    _setThread: function (threadID) {
        var thread = this.call('mail_service', 'getThread', threadID);
        this._thread = thread;
        if (thread.getType() !== 'mailbox') {
            this.call('mail_service', 'openThreadWindow', threadID);
            return $.when();
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to only store the thread state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed thread
     *
     * @override
     * @private
     */
    _storeThreadState: function () {
        if (this._thread && this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is
     * unselected
     *
     * @override
     * @private
     */
    _unselectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').removeClass('o_hidden');
    },
    /**
     * @override
     * @private
     */
    _updateThreads: function () {
        return this._updateContent(this._currentState);
    },
    /**
     * Redraws the content of the client action according to its current state.
     *
     * @private
     * @param {string} type the thread's type to display (e.g. 'mailbox_inbox',
     *   'mailbox_starred', 'dm_chat'...).
     */
    _updateContent: function (type) {
        var self = this;
        var inMailbox = type === 'mailbox_inbox' || type === 'mailbox_starred';
        if (!inMailbox && this._isInInboxTab()) {
            // we're leaving the inbox, so store the thread scrolltop
            this._storeThreadState();
        }
        var previouslyInInbox = this._isInInboxTab();
        this._currentState = type;

        // fetch content to display
        var def;
        if (inMailbox) {
            def = this._fetchAndRenderThread();
        } else {
            var allChannels = this.call('mail_service', 'getChannels');
            var channels = _.filter(allChannels, function (channel) {
                return channel.getType() === type;
            });
            def = this.call('mail_service', 'getChannelPreviews', channels);
        }
        return $.when(def).then(function (previews) {
            // update content
            if (inMailbox) {
                if (!previouslyInInbox) {
                    self.$('.o_mail_discuss_tab_pane').remove();
                    self._$mainContent.append(self._threadWidget.$el);
                    self._$mainContent.append(self._extendedComposer.$el);
                }
                self._restoreThreadState();
            } else {
                self._threadWidget.$el.detach();
                self._extendedComposer.$el.detach();
                var $content = $(QWeb.render('mail.discuss.MobileTabPane', {
                    previews: previews,
                    type: type,
                }));
                self._prepareAddThreadInput($content.find('.o_mail_add_thread input'), type);
                self._$mainContent.html($content);
            }

            // update control panel
            self.$buttons.find('button')
                         .removeClass('d-block')
                         .addClass('d-none');
            self.$buttons.find('.o_mail_discuss_button_' + type)
                         .removeClass('d-none')
                         .addClass('d-block');
            self.$buttons.find('.o_mail_discuss_button_mark_all_read')
                         .toggleClass('d-none', type !== 'mailbox_inbox')
                         .toggleClass('d-block', type === 'mailbox_inbox');
            self.$buttons.find('.o_mail_discuss_button_unstar_all')
                         .toggleClass('d-none', type !== 'mailbox_starred')
                         .toggleClass('d-block', type === 'mailbox_starred');

            // update Mailbox page buttons
            if (inMailbox) {
                self.$('.o_mail_discuss_mobile_mailboxes_buttons')
                    .removeClass('o_hidden');
                self.$('.o_mailbox_inbox_item')
                    .removeClass('btn-primary')
                    .addClass('btn-secondary');
                self.$('.o_mailbox_inbox_item[data-type=' + type + ']')
                    .removeClass('btn-secondary')
                    .addClass('btn-primary');
            } else {
                self.$('.o_mail_discuss_mobile_mailboxes_buttons')
                    .addClass('o_hidden');
            }

            // update bottom buttons
            self.$('.o_mail_mobile_tab').removeClass('active');
            // mailbox_inbox and mailbox_starred share the same tab
            type = type === 'mailbox_starred' ? 'mailbox_inbox' : type;
            self.$('.o_mail_mobile_tab[data-type=' + type + ']').addClass('active');
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onAddThread: function () {
        this.$('.o_mail_add_thread').show().find('input').focus();
    },
    /**
     * Switches to the clicked thread in the Inbox page (Inbox or Starred).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileInboxButtonClicked: function (ev) {
        var mailboxID = $(ev.currentTarget).data('type');
        this._setThread(mailboxID);
        this._updateContent(this._thread.getID());
    },
    /**
     * Switches to another tab.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileTabClicked: function (ev) {
        var type = $(ev.currentTarget).data('type');
        if (type === 'mailbox') {
            var inbox = this.call('mail_service', 'getMailbox', 'inbox');
            this._setThread(inbox);
        }
        this._updateContent(type);
    },
    /**
     * Opens a thread in a chat window (full screen in mobile).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileThreadClicked: function (ev) {
        var threadID = $(ev.currentTarget).data('preview-id');
        this.call('mail_service', 'openThreadWindow', threadID);
    },
});

});
