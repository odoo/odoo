odoo.define('mail.Discuss', function (require) {
"use strict";

var composer = require('mail.composer');
var ThreadWidget = require('mail.widget.Thread');

var AbstractAction = require('web.AbstractAction');
var config = require('web.config');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Widget : Invite People to Channel Dialog
 *
 * Popup containing a 'many2many_tags' custom input to select multiple partners.
 * Searches user according to the input, and triggers event when selection is
 * validated.
 */
var PartnerInviteDialog = Dialog.extend({
    dialog_title: _t("Invite people"),
    template: 'mail.PartnerInviteDialog',

    /**
     * @override
     * @param {integer|string} channelID id of the channel,
     *      a string for static channels (e.g. 'mailbox_inbox').
     */
    init: function (parent, title, channelID) {
        this._channelID = channelID;

        this._super(parent, {
            title: title,
            size: 'medium',
            buttons: [{
                text: _t("Invite"),
                close: true,
                classes: 'btn-primary',
                click: this._addChannel.bind(this),
            }],
        });
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$input = this.$('.o_mail_chat_partner_invite_input');
        this.$input.select2({
            width: '100%',
            allowClear: true,
            multiple: true,
            formatResult: function (item) {
                var status = QWeb.render('mail.conversation.UserStatus', {status: item.im_status});
                return $('<span>').text(item.text).prepend(status);
            },
            query: function (query) {
                self.call('chat_service', 'searchPartner', query.term, 20)
                    .then(function (partners) {
                        query.callback({
                            results: _.map(partners, function (partner) {
                                return _.extend(partner, { text: partner.label });
                            }),
                        });
                    });
            }
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {$.Promise}
     */
    _addChannel: function () {
        var self = this;
        var data = this.$input.select2('data');
        if (data.length >= 1) {
            return this._rpc({
                    model: 'mail.channel',
                    method: 'channel_invite',
                    args: [this._channelID],
                    kwargs: {partner_ids: _.pluck(data, 'id')},
                }).then(function () {
                    var names = _.escape(_.pluck(data, 'text').join(', '));
                    var notification = _.str.sprintf(_t("You added <b>%s</b> to the conversation."), names);
                    self.do_notify(_t("New people"), notification);
                    // Update list of members with the invited user, so that
                    // we can mention this user in this channel right away.
                    var channel = self.call('chat_service', 'getChannel', self._channelID);
                    channel.forceFetchMembers();
                });
        }
    },
});

var Discuss = AbstractAction.extend(ControlPanelMixin, {
    template: 'mail.discuss',
    custom_events: {
        search: '_onSearch',
    },
    events: {
        'blur .o_mail_add_channel input': '_onAddChannelBlur',
        'click .o_mail_annoying_notification_bar .fa-close': '_onCloseNotificationBar',
        'click .o_mail_conversation_item': '_onConversationClicked',
        'click .o_mail_open_channels': '_onPublicChannelsClick',
        'click .o_mail_partner_unpin': '_onUnpinChannel',
        'click .o_mail_channel_settings': '_onChannelSettingsClicked',
        'click .o_mail_request_permission': '_onRequestNotificationPermission',
        'click .o_mail_sidebar_title .o_add': '_onAddChannel',
        'keydown': '_onKeydown',
    },

    /**
     * @override
     */
    init: function (parent, action, options) {
        this._super.apply(this, arguments);

        this.action = action;
        this.action_manager = parent;
        this.dataset = new data.DataSetSearch(this, 'mail.message');
        this.displayNotificationBar = (window.Notification && window.Notification.permission === 'default');
        this.domain = [];
        this.options = options || {};

        this._conversationsScrolltop = {};
        this._composerStates = {};
        this._defaultConversationID = this.options.active_id ||
                                        this.action.context.active_id ||
                                        this.action.params.default_active_id ||
                                        'mailbox_inbox';
        this._selectedMessage = null;
        this._throttledUpdateConversations = _.throttle(this._updateConversations.bind(this), 100, { leading: false });
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var viewID = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = this
            .loadFieldView(this.dataset, viewID, 'search')
            .then(function (fieldsView) {
                self.fields_view = fieldsView;
            });
        return $.when(this._super(), this.call('chat_service', 'isReady'), def);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defaultConversation = this.call('chat_service', 'getConversation', this._defaultConversationID) ||
                                this.call('chat_service', 'getMailbox', 'inbox');

        this._basicComposer = new composer.BasicComposer(this, { mentionPartnersRestricted: true });
        this._extendedComposer = new composer.ExtendedComposer(this, { mentionPartnersRestricted: true });
        this._basicComposer.on('post_message', this, this._onPostMessage);
        this._basicComposer.on('input_focused', this, this._onComposerFocused);
        this._extendedComposer.on('post_message', this, this._onPostMessage);
        this._extendedComposer.on('input_focused', this, this._onComposerFocused);
        this._renderButtons();

        var defs = [];
        defs.push(this._renderThread());
        defs.push(this._basicComposer.appendTo(this.$('.o_mail_conversation_content')));
        defs.push(this._extendedComposer.appendTo(this.$('.o_mail_conversation_content')));
        defs.push(this._renderSearchView());

        return this.alive($.when.apply($, defs))
            .then(function () {
                return self.alive(self._setConversation(defaultConversation));
            })
            .then(function () {
                self._updateConversations();
                self._startListening();
                self._threadWidget.$el.on('scroll', null, _.debounce(function () {
                    if (self._threadWidget.getScrolltop() < 20 &&
                        !self._threadWidget.$('.o_mail_no_content').length &&
                        !self._conversation.isAllHistoryLoaded(self.domain)) {
                        self._loadMoreMessages();
                    }
                    if (self._threadWidget.isAtBottom() && self._conversation.getType() !== 'mailbox') {
                        self._conversation.markAsSeen();
                    }
                }, 100));
            });
    },
    /**
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        this._updateControlPanel();
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: this._conversation.getID(),
        });
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.off().destroy();
        }
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this.call('chat_service', 'getChatBus').trigger('discuss_open', true);
        if (this._conversation) {
            this._threadWidget.scrollToPosition(this._conversationsScrolltop[this._conversation.getID()]);
        }
        this._loadEnoughMessages();
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        this.call('chat_service', 'getChatBus').trigger('discuss_open', false);
        this._conversationsScrolltop[this._conversation.getID()] = this._threadWidget.getScrolltop();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {$.Promise}
     */
    _fetchAndRenderThread: function () {
        var self = this;
        return this._conversation.getMessages(this.domain)
            .then(function (messages) {
                self._threadWidget.render(messages, self._getThreadRenderingOptions(messages));
                self._updateButtonStatus(messages.length === 0);
                return self._loadEnoughMessages();
            });
    },
    /**
     * @private
     * @param {mail.model.Message} messages
     * @returns {Object}
     */
    _getThreadRenderingOptions: function (messages) {
        // Compute position of the 'New messages' separator, only once when joining
        // a channel to keep it in the thread when new messages arrive
        if (_.isUndefined(this.messagesSeparatorPosition)) {
            if (!this._unreadCounter) {
                this.messagesSeparatorPosition = false; // no unread message -> don't display separator
            } else {
                var message = this._conversation.getLastSeenMessage();
                this.messagesSeparatorPosition = message ? message.getID() : 'top';
            }
        }
        return {
            threadID: this._conversation.getID(),
            displayLoadMore: !this._conversation.isAllHistoryLoaded(this.domain),
            displayMarkAsRead: this._conversation.getID() === 'mailbox_inbox',
            messagesSeparatorPosition: this.messagesSeparatorPosition,
            squashCloseMessages: this._conversation.getType() !== 'mailbox' && !this._conversation.isMassMailing(),
            displayEmptyChannel: !messages.length && !this.domain.length,
            displayNoMatchFound: !messages.length && this.domain.length,
            displaySubjectOnMessages: (this._conversation.getType() !== 'mailbox' && this._conversation.isMassMailing()) ||
                                        this._conversation.getID() === 'mailbox_inbox',
            displayEmailIcon: false,
            displayReplyIcon: true,
        };
    },
    /**
     * Ensures that enough messages have been loaded to fill the entire screen
     * (this is particularily important because remaining messages can only be
     * loaded when scrolling to the top, so they can't be loaded if there is no
     * scrollbar)
     *
     * @returns {Deferred} resolved when there are enough messages to fill the
     *   screen, or when there is no more message to fetch
     */
    _loadEnoughMessages: function () {
        var loadMoreMessages = this._threadWidget.el.clientHeight &&
            this._threadWidget.el.clientHeight === this._threadWidget.el.scrollHeight &&
            !this._conversation.isAllHistoryLoaded(this.domain);
        if (loadMoreMessages) {
            return this._loadMoreMessages().then(this._loadEnoughMessages.bind(this));
        }
    },
    /**
     * Load more messages for the current thread
     *
     * @private
     * @returns {$.Promise}
     */
    _loadMoreMessages: function () {
        var self = this;
        var oldestMsgID = this.$('.o_thread_message').first().data('messageId');
        var oldestMsgSelector = '.o_thread_message[data-message-id="' + oldestMsgID + '"]';
        var offset = -dom.getPosition(document.querySelector(oldestMsgSelector)).top;
        return this._conversation.getMessages(this.domain, true)
            .then(function (messages) {
                if (self.messagesSeparatorPosition === 'top') {
                    self.messagesSeparatorPosition = undefined; // reset value to re-compute separator position
                }
                self._threadWidget.render(messages, self._getThreadRenderingOptions(messages));
                offset += dom.getPosition(document.querySelector(oldestMsgSelector)).top;
                self._threadWidget.scrollToPosition(offset);
            });
    },
    /**
     * Binds handlers on the given $input to make them autocomplete and/or
     * create channels.
     *
     * @private
     * @param {JQuery} $input the input to prepare
     * @param {string} type the type of channel to create ('dm', 'public' or
     *   'private')
     */
    _prepareAddChannelInput: function ($input, type) {
        var self = this;
        if (type === 'public') {
            $input.autocomplete({
                source: function (request, response) {
                    self._lastSearchVal = _.escape(request.term);
                    self._searchChannel(self._lastSearchVal).done(function (result){
                        result.push({
                            'label':  _.str.sprintf('<strong>'+_t("Create %s")+'</strong>', '<em>"#'+self._lastSearchVal+'"</em>'),
                            'value': '_create',
                        });
                        response(result);
                    });
                },
                select: function (ev, ui) {
                    if (self._lastSearchVal) {
                        if (ui.item.value === '_create') {
                            self.call('chat_service', 'createChannel', self._lastSearchVal, 'public');
                        } else {
                            self.call('chat_service', 'joinChannel', ui.item.id);
                        }
                    }
                },
                focus: function (ev) {
                    ev.preventDefault();
                },
                html: true,
            });
        } else if (type === 'private') {
            $input.on('keyup', this, function (ev) {
                var name = _.escape($(ev.target).val());
                if (ev.which === $.ui.keyCode.ENTER && name) {
                    self.call('chat_service', 'createChannel', name, 'private');
                }
            });
        } else if (type === 'dm') {
            $input.autocomplete({
                source: function (request, response) {
                    self._lastSearchVal = _.escape(request.term);
                    self.call('chat_service', 'searchPartner', self._lastSearchVal, 10).done(response);
                },
                select: function (ev, ui) {
                    var partnerID = ui.item.id;
                    var dm = self.call('chat_service', 'getDmFromPartnerID', partnerID);
                    if (dm) {
                        self._setConversation(dm);
                    } else {
                        self.call('chat_service', 'createChannel', partnerID, 'dm');
                    }
                    // clear the input
                    $(this).val('');
                    return false;
                },
                focus: function (ev) {
                    ev.preventDefault();
                },
            });
        }
    },
    /**
     * @private
     */
    _renderButtons: function () {
        this.$buttons = $(QWeb.render('mail.conversation.ControlButtons', { debug: session.debug }));
        this.$buttons.find('button').css({display:'inline-block'});
        this.$buttons.on('click', '.o_mail_conversation_button_invite', this._onInviteButtonClicked.bind(this));
        this.$buttons.on('click', '.o_mail_conversation_button_mark_read', this._onMarkAllReadClicked.bind(this));
        this.$buttons.on('click', '.o_mail_conversation_button_unstar_all', this._onUnstarAllClicked.bind(this));
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _renderSearchView: function () {
        var self = this;
        var options = {
            $buttons: $('<div>'),
            action: this.action,
            disable_groupby: true,
        };
        this.searchview = new SearchView(this, this.dataset, this.fields_view, options);
        return this.alive(this.searchview.appendTo($('<div>'))).then(function () {
            self.$searchview_buttons = self.searchview.$buttons.contents();
            // manually call do_search to generate the initial domain and filter
            // the messages in the default channel
            self.searchview.do_search();
        });
    },
    /**
     * @private
     * @param {string} template
     * @param {Object} context rendering context
     * @param {integer} [timeout=20000] the delay before the snackbar disappears
     */
    _renderSnackbar: function (template, context, timeout) {
        if (this.$snackbar) {
            this.$snackbar.remove();
        }
        timeout = timeout || 20000;
        this.$snackbar = $(QWeb.render(template, context));
        this.$('.o_mail_conversation_content').append(this.$snackbar);
        // Hide snackbar after [timeout] milliseconds (by default, 20s)
        var $snackbar = this.$snackbar;
        setTimeout(function () { $snackbar.fadeOut(); }, timeout);
    },
    /**
     * Renders, binds events and appends a thread widget.
     *
     * @private
     * @returns {Deferred}
     */
    _renderThread: function () {
        var self = this;
        this._threadWidget = new ThreadWidget(this, {
            displayHelp: true,
            loadMoreOnScroll: true
        });

        this._threadWidget.on('redirect', this, function (resModel, resID) {
            self.call('chat_service', 'redirect', resModel, resID, self._setConversation.bind(self));
        });
        this._threadWidget.on('redirect_to_channel', this, function (channelID) {
            self.call('chat_service', 'joinChannel', channelID).then(this._setConversation.bind(this));
        });
        this._threadWidget.on('load_more_messages', this, this._loadMoreMessages);
        this._threadWidget.on('mark_as_read', this, function (messageID) {
            self.call('chat_service', 'markAsRead', [messageID]);
        });
        this._threadWidget.on('toggle_star_status', this, function (messageID) {
            var message = self.call('chat_service', 'getMessage', messageID);
            message.toggleStarStatus();
        });
        this._threadWidget.on('select_message', this, this._selectMessage);
        this._threadWidget.on('unselect_message', this, this._unselectMessage);

        return this._threadWidget.appendTo(this.$('.o_mail_conversation_content'));
    },
    /**
     * @private
     * @param {mail.model.Channel} channel
     */
    _restoreComposerState: function (channel) {
        var composer = channel.isMassMailing() ? this._extendedComposer : this._basicComposer;
        var composerState = this._composerStates[channel.getUUID()];
        if (composerState) {
            composer.setState(composerState);
        }
    },
    /**
     * Restores the scroll position and composer state of the current conversation
     *
     * @private
     */
    _restoreConversationState: function () {
        var $newMessagesSeparator = this.$('.o_thread_new_messages_separator');
        if ($newMessagesSeparator.length) {
            this._threadWidget.$el.scrollTo($newMessagesSeparator);
        } else {
            var newConvoScrolltop = this._conversationsScrolltop[this._conversation.getID()];
            this._threadWidget.scrollToPosition(newConvoScrolltop);
        }
        if (this._conversation.getType() !== 'mailbox') {
            this._restoreComposerState(this._conversation);
        }
    },
    /**
     * @private
     * @param {string} searchVal
     * @returns {$.Promise<Array>}
     */
    _searchChannel: function (searchVal){
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_search_to_join',
                args: [searchVal]
            })
            .then(function (result){
                var values = [];
                _.each(result, function (channel){
                    var escapedName = _.escape(channel.name);
                    values.push(_.extend(channel, {
                        'value': escapedName,
                        'label': escapedName,
                    }));
                });
                return values;
            });
    },
    /**
     * @private
     * @param {integer} messageID
     */
    _selectMessage: function (messageID) {
        this.$el.addClass('o_mail_selection_mode');
        var message = this.call('chat_service', 'getMessage', messageID);
        this._selectedMessage = message;
        var subject = "Re: " + message.getDocumentName();
        this._extendedComposer.setSubject(subject);

        if (this._conversation.getType() !== 'mailbox') {
            this._basicComposer.do_hide();
        }
        this._extendedComposer.do_show();

        this._threadWidget.scrollToMessage({msgID: messageID, duration: 200, onlyIfNecessary: true});
        this._extendedComposer.focus('body');
    },
    /**
     * @private
     * @param {mail.model.Conversation} conversation
     * @returns {$.Promise}
     */
    _setConversation: function (conversation) {
        var self = this;

        // Store scroll position and composer state of the previous conversation
        this._storeConversationState();

        this._conversation = conversation;
        this.messagesSeparatorPosition = undefined; // reset value on channel change
        this._unreadCounter = this._conversation.getUnreadCounter();
        if (this.$snackbar) {
            this.$snackbar.remove();
        }

        this.action.context.active_id = conversation.getID();
        this.action.context.active_ids = [conversation.getID()];

        return this._fetchAndRenderThread().then(function () {
            // Mark channel's messages as read and clear needactions
            if (conversation.getType() !== 'mailbox') {
                conversation.markAsSeen();
            }
            // Restore scroll position and composer of the new current conversation
            self._restoreConversationState();

            // Update control panel before focusing the composer, otherwise focus is on the searchview
            self.set("title", '#' + conversation.getName());
            self._updateControlPanel();
            self._updateControlPanelButtons(conversation);

            // Display and focus the adequate composer, and unselect possibly selected message
            // to prevent sending messages as reply to that message
            self._unselectMessage();

            self.action_manager.do_push_state({
                action: self.action.id,
                active_id: self._conversation.getID(),
            });
        });
    },
    /**
     * Binds handlers on chat bus events
     *
     * @private
     */
    _startListening: function () {
        var chatBus = this.call('chat_service', 'getChatBus');
        chatBus.on('open_conversation', this, this._setConversation);
        chatBus.on('new_message', this, this._onNewMessage);
        chatBus.on('update_message', this, this._onMessageUpdated);
        chatBus.on('new_channel', this, this._onNewChannel);
        chatBus.on('anyone_listening', this, this._onAnyoneListening);
        chatBus.on('unsubscribe_from_channel', this, this._onChannelLeft);
        chatBus.on('update_needaction', this, this._throttledUpdateConversations);
        chatBus.on('update_starred', this, this._throttledUpdateConversations);
        chatBus.on('update_conversation_unread_counter', this, this._throttledUpdateConversations);
        chatBus.on('update_dm_presence', this, this._throttledUpdateConversations);
        chatBus.on('activity_updated', this, this._throttledUpdateConversations);
    },
    /**
     * @private
     * @param {mail.model.Channel} channel
     */
    _storeComposerState: function (channel) {
        var composer = channel.isMassMailing() ? this._extendedComposer : this._basicComposer;
        this._composerStates[channel.getUUID()] = composer.getState();
        composer.clearComposer();
    },
    /**
     * Stores the scroll position of the current conversation.
     * For channels, also stores composer state.
     *
     * @private
     */
    _storeConversationState: function () {
        if (this._conversation) {
            this._conversationsScrolltop[this._conversation.getID()] = this._threadWidget.getScrolltop();
            if (this._conversation.getType() !== 'mailbox') {
                this._storeComposerState(this._conversation);
            }
        }
    },
    /**
     * @private
     */
    _unselectMessage: function () {
        this._basicComposer.do_toggle(this._conversation.getType() !== 'mailbox' && !this._conversation.isMassMailing());
        this._extendedComposer.do_toggle(this._conversation.getType() !== 'mailbox' && !!this._conversation.isMassMailing());

        if (!config.device.touch) {
            var composer = this._conversation.getType() !== 'mailbox' && this._conversation.isMassMailing() ?
                            this._extendedComposer :
                            this._basicComposer;
            composer.focus();
        }
        this.$el.removeClass('o_mail_selection_mode');
        this._threadWidget.unselectMessage();
        this._selectedMessage = null;
    },
    /**
     * @private
     * @param {boolean} disabled
     * @param {string} type
     */
    _updateButtonStatus: function (disabled, type) {
        if (this._conversation.getID() === 'mailbox_inbox') {
            this.$buttons
                .find('.o_mail_conversation_button_mark_read')
                .toggleClass('disabled', disabled);
            // Display Rainbowman when all inbox messages are read through
            // 'MARK ALL READ' or marking last inbox message as read
            if (disabled && type === 'mark_as_read') {
                this.trigger_up('show_effect', {
                    message: _t("Congratulations, your inbox is empty!"),
                    type: 'rainbow_man',
                });
            }
        }
        if (this._conversation.getID() === 'mailbox_starred') {
            this.$buttons
                .find('.o_mail_conversation_button_unstar_all')
                .toggleClass('disabled', disabled);
        }
    },
    /**
     * @private
     */
    _updateControlPanel: function () {
        this.update_control_panel({
            cp_content: {
                $buttons: this.$buttons,
                $searchview: this.searchview.$el,
                $searchview_buttons: this.$searchview_buttons,
            },
            searchview: this.searchview,
        });
    },
    /**
     * Updates the control panel buttons visibility based on conversation type
     *
     * @private
     * @param {mail.model.Conversation} conversation
     */
    _updateControlPanelButtons: function (conversation) {
        // Hide 'unsubscribe' button in state channels and DM and channels with group-based subscription
        this.$buttons
            .find('.o_mail_conversation_button_invite, .o_mail_conversation_button_settings')
            .toggle(conversation.getType() !== 'dm' && conversation.getType() !== 'mailbox');
        this.$buttons
            .find('.o_mail_conversation_button_mark_read')
            .toggle(conversation.getID() === 'mailbox_inbox')
            .removeClass('o_hidden');
        this.$buttons
            .find('.o_mail_conversation_button_unstar_all')
            .toggle(conversation.getID() === 'mailbox_starred')
            .removeClass('o_hidden');

        this.$('.o_mail_conversation_item')
            .removeClass('o_active')
            .filter('[data-conversation-id=' + conversation.getID() + ']')
            .removeClass('o_unread_message')
            .addClass('o_active');
    },
    /**
     * Renders the mainside bar with current conversations
     *
     * @private
     */
    _updateConversations: function () {
        var self = this;
        var inbox = this.call('chat_service', 'getMailbox', 'inbox');
        var starred = this.call('chat_service', 'getMailbox', 'starred');

        var $sidebar = $(QWeb.render('mail.conversation.Sidebar', {
            activeChannelID: this._conversation ? this._conversation.getID(): undefined,
            conversations: this.call('chat_service', 'getConversations'),
            needactionCounter: inbox.getMailboxCounter(),
            starredCounter: starred.getMailboxCounter(),
        }));
        this.$('.o_mail_conversation_sidebar').html($sidebar.contents());
        _.each(['dm', 'public', 'private'], function (type) {
            var $input = self.$('.o_mail_add_channel[data-type=' + type + '] input');
            self._prepareAddChannelInput($input, type);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddChannel: function (ev) {
        ev.preventDefault();
        var type = $(ev.target).data('type');
        this.$('.o_mail_add_channel[data-type=' + type + ']')
            .show()
            .find('input').focus();
    },
    /**
     * @private
     */
    _onAddChannelBlur: function () {
        this.$('.o_mail_add_channel').hide();
    },
    /**
     * @private
     * @param {mail.model.Channel} channel
     * @param {Object} query
     */
    _onAnyoneListening: function (channel, query) {
        query.isDisplayed = query.isDisplayed ||
                            (channel.getID() === this._conversation.getID() && this._threadWidget.isAtBottom());
    },
    /**
     * @private
     * @param {integer|string} channelID
     */
    _onChannelLeft: function (channelID) {
        if (this._conversation.getID() === channelID) {
            var inbox = this.call('chat_service', 'getMailbox', 'inbox');
            this._setConversation(inbox);
        }
        this._updateConversations();
        delete this._conversationsScrolltop[channelID];
    },
    /**
     * @private
     */
    _onComposerFocused: function () {
        var composer = this._conversation.isMassMailing() ? this._extendedComposer : this._basicComposer;
        var commands = this._conversation.getCommands();
        var partners = this._conversation.getMentionPartnerSuggestions();
        composer.mentionSetEnabledCommands(commands);
        composer.mentionSetPrefetchedPartners(partners);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onConversationClicked: function (ev) {
        ev.preventDefault();
        var conversationID = $(ev.currentTarget).data('conversation-id');
        var conversation = this.call('chat_service', 'getConversation', conversationID);
        this._setConversation(conversation);
    },
    /**
     * @private
     */
    _onMarkAllReadClicked: function () {
        this._conversation.markAllAsRead(this.domain);
    },
    /**
     * @private
     * @param {mail.model.Message} message
     * @param {string} type the channel type
     */
    _onMessageUpdated: function (message, type) {
        var self = this;
        var currentConversationID = this._conversation.getID();
        if ((currentConversationID === 'mailbox_starred' && !message.isStarred()) ||
            (currentConversationID === 'mailbox_inbox' && !message.isNeedaction())) {
                this._conversation.getMessages(this.domain)
                    .then(function (messages) {
                        var options = self._getThreadRenderingOptions(messages);
                        self._threadWidget.removeMessageAndRender(message.getID(), messages, options)
                            .then(function () {
                                self._updateButtonStatus(messages.length === 0, type);
                            });
                    });
        } else if (_.contains(message.getConversationIDs(), currentConversationID)) {
            this._fetchAndRenderThread();
        }
    },
    /**
     * @private
     * @param {mail.model.Channel} channel
     */
    _onNewChannel: function (channel) {
        this._updateConversations();
        if (channel.autoswitch) {
            this._setConversation(channel);
        }
    },
    /**
     * @private
     * @param {mail.model.Message} message
     */
    _onNewMessage: function (message) {
        var self = this;
        if (_.contains(message.getConversationIDs(), this._conversation.getID())) {
            if (this._conversation.getType() !== 'mailbox' && this._threadWidget.isAtBottom()) {
                this._conversation.markAsSeen();
            }
            var shouldScroll = this._threadWidget.isAtBottom();
            this._fetchAndRenderThread().then(function () {
                if (shouldScroll) {
                    self._threadWidget.scrollToMessage({ msgID: message.getID() });
                }
            });
        }
        // Re-render sidebar to indicate that there is a new message in the corresponding conversations
        this._updateConversations();
        // Dump scroll position of conversations in which the new message arrived
        this._conversationsScrolltop = _.omit(this._conversationsScrolltop, message.getConversationIDs());
    },
    /**
     * @private
     * @param {Object} message
     */
    _onPostMessage: function (message) {
        var self = this;
        if (this._selectedMessage) {
            message.subtype = this._selectedMessage.isNote() ? 'mail.mt_note': 'mail.mt_comment';
            message.subtype_id = false;
            message.messageType = 'comment';
            message.content_subtype = 'html';
        }
        this._conversation.postMessage(message)
            .then(function () {
                if (self._selectedMessage) {
                    self._renderSnackbar('mail.conversation.MessageSentSnackbar', { documentName: self._selectedMessage.getDocumentName() }, 5000);
                    self._unselectMessage();
                } else {
                    self._threadWidget.scrollToBottom();
                }
            })
            .fail(function () {
                // todo: display notification
            });
    },
    /**
     * @private
     */
    _onPublicChannelsClick: function () {
        this.do_action({
            name: _t("Public Channels"),
            type: 'ir.actions.act_window',
            res_model: 'mail.channel',
            views: [[false, 'kanban'], [false, 'form']],
            domain: [['public', '!=', 'private']],
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
    /**
     * @private
     */
    _onCloseNotificationBar: function () {
        this.$('.o_mail_annoying_notification_bar').slideUp();
    },
    /**
     * Invite button is only for channels (not mailboxes)
     *
     * @private
     */
    _onInviteButtonClicked: function () {
        var title = _.str.sprintf(_t("Invite people to #%s"), this._conversation.getName());
        new PartnerInviteDialog(this, title, this._conversation.getID()).open();
    },
    /**
     * @private
     * @param {KeyEvent} ev
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ESCAPE && this._selectedMessage) {
            this._unselectMessage();
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onRequestNotificationPermission: function (ev) {
        var self = this;
        ev.preventDefault();
        this.$('.o_mail_annoying_notification_bar').slideUp();
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then(function (value) {
                if (value !== 'granted') {
                    self.call('bus_service', 'sendNotification', self, _t("Permission denied"),
                        _t("Odoo will not have the permission to send native notifications on this device."));
                } else {
                    self.call('bus_service', 'sendNotification', self, _t("Permission granted"),
                        _t("Odoo has now the permission to send you native notifications on this device."));
                }
            });
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSearch: function (ev) {
        ev.stopPropagation();
        var session = this.getSession();
        var result = pyeval.eval_domains_and_contexts({
            domains: ev.data.domains,
            contexts: [session.user_context],
        });
        this.domain = result.domain;
        if (this._conversation) {
            // initially (when _onSearch is called manually), there is no
            // conversation set yet, so don't try to fetch and render the thread as
            // this will be done as soon as the default conversation is set
            this._fetchAndRenderThread();
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChannelSettingsClicked: function (ev) {
        var channelID = $(ev.target).data('conversation-id');
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'mail.channel',
            res_id: channelID,
            views: [[false, 'form']],
            target: 'current'
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onUnpinChannel: function (ev) {
        ev.stopPropagation();
        var channelID = $(ev.target).data('conversation-id');
        var channel = this.call('chat_service', 'getChannel', channelID);
        channel.unsubscribe();
    },
    /**
     * @private
     */
    _onUnstarAllClicked: function () {
        this.call('chat_service', 'unstarAll');
    },
});

core.action_registry.add('mail.chat.instant_messaging', Discuss);

return Discuss;

});
