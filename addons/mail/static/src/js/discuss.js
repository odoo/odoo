odoo.define('mail.chat_discuss', function (require) {
"use strict";

var ChatThread = require('mail.ChatThread');
var composer = require('mail.composer');

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
    dialog_title: _t('Invite people'),
    template: "mail.PartnerInviteDialog",

    /**
     * @override
     * @param {integer|string} channelID id of the channel,
     *      a string for static channels (e.g. 'channel_inbox').
     */
    init: function (parent, title, channelID) {
        this.channelID = channelID;

        this._super(parent, {
            title: title,
            size: "medium",
            buttons: [{
                text: _t("Invite"),
                close: true,
                classes: "btn-primary",
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
                var status = QWeb.render('mail.chat.UserStatus', {status: item.im_status});
                return $('<span>').text(item.text).prepend(status);
            },
            query: function (query) {
                self.call('chat_manager', 'searchPartner', query.term, 20)
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
                    args: [this.channelID],
                    kwargs: {partner_ids: _.pluck(data, 'id')},
                }).then(function () {
                    var names = _.escape(_.pluck(data, 'text').join(', '));
                    var notification = _.str.sprintf(_t('You added <b>%s</b> to the conversation.'), names);
                    self.do_notify(_t('New people'), notification);
                    // Clear the membersDeferred to fetch again the partner
                    // when getMentionPartnerSuggestions from the chatManager is triggered
                    var channel = self.call('chat_manager', 'getChannel', self.channelID);
                    delete channel.membersDeferred;
                });
        }
    },
});

/**
 * Widget : Moderator reject message dialog
 *
 * Popup containing message title and reject message body.
 * This let the moderator provide a reason for rejecting the messages.
 */
var ModeratorRejectMessageDialog = Dialog.extend({
    template: "mail.ModeratorRejectMessageDialog",

    /**
     * @override
     * @param {web.Widget} parent
     * @param {Object} params
     * @param {integer[]} params.messageIDs list of message IDs to send
     *   'reject' decision reason
     * @param {function} params.proceedReject a function to call when the
     *   moderator confirms the reason for rejecting the messages. This
     *   function passes an object as the reason for reject, which is
     *   structured as follow:
     *
     *          {
     *              title: <string>,
     *              comment: <string>,
     *          }
     */
    init: function (parent, params) {
        this._messageIDs = params.messageIDs;
        this._proceedReject = params.proceedReject;
        this._super(parent, {
            title: _t('Send explanation to author'),
            size: "medium",
            buttons: [{
                text: _t("Send"),
                close: true,
                classes: "btn-primary",
                click: _.bind(this._onSendClicked, this),
            }],
        });
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the moderator would like to submit reason for rejecting the
     * messages.
     *
     * @private
     */
    _onSendClicked: function () {
        var title = this.$('#message_title').val();
        var comment = this.$('#reject_message').val();
        if (title && comment) {
            this._proceedReject({
                title: title,
                comment: comment
            });
        }
    },
});

var Discuss = AbstractAction.extend(ControlPanelMixin, {
    template: 'mail.discuss',
    custom_events: {
        message_moderation: '_onMessageModeration',
        search: '_onSearch',
        update_moderation_buttons: '_onUpdateModerationButtons',
    },
    events: {
        'blur .o_mail_add_channel input': '_onAddChannelBlur',
        'click .o_mail_annoying_notification_bar .fa-close': '_onCloseNotificationBar',
        'click .o_mail_chat_channel_item': '_onChannelClicked',
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
        this.action_manager = parent;
        this.dataset = new data.DataSetSearch(this, 'mail.message');
        this.domain = [];
        this.action = action;
        this.options = options || {};
        this.channelsScrolltop = {};
        this.throttledUpdateChannels = _.throttle(this._updateChannels.bind(this), 100, { leading: false });
        this.notification_bar = (window.Notification && window.Notification.permission === "default");
        this.selected_message = null;
        this.composerStates = {};
        this.defaultChannelID = this.options.active_id ||
                                 this.action.context.active_id ||
                                 this.action.params.default_active_id ||
                                 'channel_inbox';
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var viewID = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = this
            .loadFieldView(this.dataset, viewID, 'search')
            .then(function (fields_view) {
                self.fields_view = fields_view;
            });
        return $.when(this._super(), this.call('chat_manager', 'isReady'), def);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defaultChannel = this.call('chat_manager', 'getChannel', this.defaultChannelID) ||
                                this.call('chat_manager', 'getChannel', 'channel_inbox');

        this.basicComposer = new composer.BasicComposer(this, {mention_partners_restricted: true});
        this.extendedComposer = new composer.ExtendedComposer(this, {mention_partners_restricted: true});
        this.basicComposer.on('post_message', this, this._onPostMessage);
        this.basicComposer.on('input_focused', this, this._onComposerFocused);
        this.extendedComposer.on('post_message', this, this._onPostMessage);
        this.extendedComposer.on('input_focused', this, this._onComposerFocused);
        this._renderButtons();

        var defs = [];
        defs.push(this._renderThread());
        defs.push(this.basicComposer.appendTo(this.$('.o_mail_chat_content')));
        defs.push(this.extendedComposer.appendTo(this.$('.o_mail_chat_content')));
        defs.push(this._renderSearchView());

        return this.alive($.when.apply($, defs))
            .then(function () {
                return self.alive(self._setChannel(defaultChannel));
            })
            .then(function () {
                self._updateChannels();
                self._startListening();
                self.thread.$el.on("scroll", null, _.debounce(function () {
                    if (self.thread.get_scrolltop() < 20 &&
                        !self.thread.$('.o_mail_no_content').length &&
                        !self.call('chat_manager', 'isAllHistoryLoaded', self.channel, self.domain)) {
                        self._loadMoreMessages();
                    }
                    if (self.thread.is_at_bottom()) {
                        self.call('chat_manager', 'markChannelAsSeen', self.channel);
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
            active_id: this.channel.id,
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
        this.call('chat_manager', 'getChatBus').trigger('discuss_open', true);
        if (this.channel) {
            this.thread.scroll_to({offset: this.channelsScrolltop[this.channel.id]});
        }
        this._loadEnoughMessages();
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        this.call('chat_manager', 'getChatBus').trigger('discuss_open', false);
        this.channelsScrolltop[this.channel.id] = this.thread.get_scrolltop();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Ban the authors of the messages with ID in `messageIDs`
     * Show a confirmation dialog to the moderator.
     *
     * @private
     * @param {integer[]} messageIDs IDs of messages for which we should ban authors
     */
    _banAuthorsFromMessageIDs: function (messageIDs) {
        var self = this;
        var emailList = _.map(messageIDs, function (messageID) {
            return self.call('chat_manager', 'getMessage', messageID).email_from;
        }).join(", ");
        var text = _.str.sprintf(_t("You are going to ban: %s. Do you confirm the action?"), emailList);
        var options = {
            confirm_callback: function () {
                self._moderateMessages(messageIDs, 'ban');
            }
        };
        Dialog.confirm(this, text, options);
    },
    /**
     * Discard the messages with ID in `messageIDs`
     * Show a confirmation dialog to the moderator.
     *
     * @private
     * @param {integer[]]} messageIDs list of message IDs to discard
     */
    _discardMessages: function (messageIDs) {
        var self = this;
        var num = messageIDs.length;
        var text;
        if (num > 1) {
            text = _.str.sprintf(_t("You are going to discard %s messages. Do you confirm the action?"), num);
        } else if (num === 1) {
            text = _t("You are going to discard 1 message. Do you confirm the action?");
        }
        var options = {
            confirm_callback: function () {
                self._moderateMessages(messageIDs, 'discard');
            }
        };
        Dialog.confirm(this, text, options);
    },
    /**
     * @private
     * @returns {$.Promise}
     */
    _fetchAndRenderThread: function () {
        var self = this;
        return this.call('chat_manager', 'getMessages', {
                channelID: this.channel.id,
                domain: this.domain
            }).then(function (messages) {
                self.thread.render(messages, self._getThreadRenderingOptions(messages));
                self._updateButtonStatus(messages.length === 0);
                return self._loadEnoughMessages();
            });
    },
    /**
     * @private
     * @param {Object} messages
     * @returns {Object}
     */
    _getThreadRenderingOptions: function (messages) {
        // Compute position of the 'New messages' separator, only once when joining
        // a channel to keep it in the thread when new messages arrive
        if (_.isUndefined(this.messages_separator_position)) {
            if (!this.unread_counter) {
                this.messages_separator_position = false; // no unread message -> don't display separator
            } else {
                var msg = this.call('chat_manager', 'getLastSeenMessage', this.channel);
                this.messages_separator_position = msg ? msg.id : 'top';
            }
        }
        return {
            channel_id: this.channel.id,
            display_load_more: !this.call('chat_manager', 'isAllHistoryLoaded', this.channel, this.domain),
            display_needactions: this.channel.display_needactions,
            messages_separator_position: this.messages_separator_position,
            squash_close_messages: this.channel.type !== 'static' && !this.channel.mass_mailing,
            display_empty_channel: !messages.length && !this.domain.length,
            display_no_match: !messages.length && this.domain.length,
            display_subject: this.channel.mass_mailing || this.channel.id === "channel_inbox" || this.channel.id === "channel_moderation",
            display_email_icon: false,
            display_reply_icon: true,
        };
    },
    /**
     * Determine the action to apply on messages with ID in `messageIDs`
     * based on the moderation decision `decision`.
     *
     * @private
     * @param {number[]} messageIDs list of message ids that are moderated
     * @param {string} decision of the moderator, could be either 'reject',
     *   'discard', 'ban', 'accept', 'allow'.
     */
     _handleModerationDecision: function (messageIDs, decision) {
        if (messageIDs) {
            if (decision === 'reject') {
                this._rejectMessages(messageIDs);
            } else if (decision === 'discard') {
                this._discardMessages(messageIDs);
            } else if (decision === 'ban') {
                this._banAuthorsFromMessageIDs(messageIDs);
            } else {
                // other decisions do not need more information,
                // confirmation dialog, etc.
                this._moderateMessages(messageIDs, decision);
            }
        }
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
        var loadMoreMessages = this.thread.el.clientHeight &&
            this.thread.el.clientHeight === this.thread.el.scrollHeight &&
            !this.call('chat_manager', 'isAllHistoryLoaded', this.channel, this.domain);
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
        return this.call('chat_manager', 'getMessages', {
                channelID: this.channel.id,
                domain: this.domain,
                loadMore: true
            })
            .then(function (messages) {
                if (self.messages_separator_position === 'top') {
                    self.messages_separator_position = undefined; // reset value to re-compute separator position
                }
                self.thread.render(messages, self._getThreadRenderingOptions(messages));
                offset += dom.getPosition(document.querySelector(oldestMsgSelector)).top;
                self.thread.scroll_to({offset: offset});
            });
    },
    /**
     * Apply the moderation decision `decision` on the messages with ID in
     * `messageIDs`.
     *
     * @private
     * @param {integer[]} messageIDs list of message IDs to apply the
     *   moderation decision.
     * @param {string} decision the moderation decision to apply on the
     *   messages. Could be either 'reject', 'discard', 'ban', 'accept',
     *   or 'allow'.
     * @param {Object|undefined} [kwargs] optional data to pass on
     *   message moderation. This is provided when rejecting the messages
     *   for which title and comment give reason(s) for reject.
     * @param {string} [kwargs.title]
     * @param {string} [kwargs.comment]
     * @return {undefined|$.Promise}
     */
    _moderateMessages: function (messageIDs, decision, kwargs) {
        if (messageIDs.length && decision) {
            return this._rpc({
                model: 'mail.message',
                method: 'moderate',
                args: [messageIDs, decision],
                kwargs: kwargs
            });
        }
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
                    self.last_search_val = _.escape(request.term);
                    self._searchChannel(self.last_search_val).done(function (result){
                        result.push({
                            'label':  _.str.sprintf('<strong>'+_t("Create %s")+'</strong>', '<em>"#'+self.last_search_val+'"</em>'),
                            'value': '_create',
                        });
                        response(result);
                    });
                },
                select: function (event, ui) {
                    if (self.last_search_val) {
                        if (ui.item.value === '_create') {
                            self.call('chat_manager', 'createChannel', self.last_search_val, "public");
                        } else {
                            self.call('chat_manager', 'joinChannel', ui.item.id);
                        }
                    }
                },
                focus: function (event) {
                    event.preventDefault();
                },
                html: true,
            });
        } else if (type === 'private') {
            $input.on('keyup', this, function (event) {
                var name = _.escape($(event.target).val());
                if (event.which === $.ui.keyCode.ENTER && name) {
                    self.call('chat_manager', 'createChannel', name, "private");
                }
            });
        } else if (type === 'dm') {
            $input.autocomplete({
                source: function (request, response) {
                    self.last_search_val = _.escape(request.term);
                    self.call('chat_manager', 'searchPartner', self.last_search_val, 10).done(response);
                },
                select: function (event, ui) {
                    var partner_id = ui.item.id;
                    var dm = self.call('chat_manager', 'getDmFromPartnerID', partner_id);
                    if (dm) {
                        self._setChannel(dm);
                    } else {
                        self.call('chat_manager', 'createChannel', partner_id, "dm");
                    }
                    // clear the input
                    $(this).val('');
                    return false;
                },
                focus: function (event) {
                    event.preventDefault();
                },
            });
        }
    },
    /**
     * Reject the messages
     *
     * The moderator must provide a reason for reject, and may also
     * cancel his action.
     *
     * @private
     * @param {number[]]} messageIDs list of message IDs to reject
     */
    _rejectMessages: function (messageIDs) {
        var self = this;
        new ModeratorRejectMessageDialog(this, {
            messageIDs: messageIDs,
            proceedReject: function (reason) {
                self._moderateMessages(messageIDs, 'reject', reason);
            }
        }).open();
    },
    /**
     * @private
     */
    _renderButtons: function () {
        this.$buttons = $(QWeb.render("mail.chat.ControlButtons", {debug: session.debug}));
        this.$buttons.find('button').css({display:"inline-block"});
        this.$buttons.on('click', '.o_mail_chat_button_invite', this._onInviteButtonClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_mark_read', this._onMarkAllReadClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_unstar_all', this._onUnstarAllClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_moderate_all', this._onModerateAllClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_select_all', this._onSelectAllClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_unselect_all', this._onUnselectAllClicked.bind(this));
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _renderSearchView: function () {
        var self = this;
        var options = {
            $buttons: $("<div>"),
            action: this.action,
            disable_groupby: true,
        };
        this.searchview = new SearchView(this, this.dataset, this.fields_view, options);
        return this.alive(this.searchview.appendTo($("<div>"))).then(function () {
            self.$searchview_buttons = self.searchview.$buttons.contents();
            // manually call do_search to generate the initial domain and filter
            // the messages in the default channel
            self.searchview.do_search();
        });
    },
    /**
     * @private
     * @param {Object} options
     * @returns {JQuery}
     */
    _renderSidebar: function (options) {
        return $(QWeb.render("mail.chat.Sidebar", options));
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
        this.$('.o_mail_chat_content').append(this.$snackbar);
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
        this.thread = new ChatThread(this, {display_help: true, loadMoreOnScroll: true});

        this.thread.on('redirect', this, function (resModel, resID) {
            this.call('chat_manager', 'redirect', resModel, resID, this._setChannel.bind(this));
        });
        this.thread.on('redirect_to_channel', this, function (channelID) {
            this.call('chat_manager', 'joinChannel', channelID).then(this._setChannel.bind(this));
        });
        this.thread.on('load_more_messages', this, this._loadMoreMessages);
        this.thread.on('mark_as_read', this, function (messageID) {
            this.call('chat_manager', 'markAsRead', [messageID]);
        });
        this.thread.on('toggle_star_status', this, function (messageID) {
            this.call('chat_manager', 'toggleStarStatus', messageID);
        });
        this.thread.on('select_message', this, this._selectMessage);
        this.thread.on('unselect_message', this, this._unselectMessage);
        return this.thread.appendTo(this.$('.o_mail_chat_content'));
    },
    /**
     * Restores the scroll position and composer state of the current channel
     *
     * @private
     */
    _restoreChannelState: function () {
        var $newMessagesSeparator = this.$('.o_thread_new_messages_separator');
        if ($newMessagesSeparator.length) {
            this.thread.$el.scrollTo($newMessagesSeparator);
        } else {
            var newChannelScrolltop = this.channelsScrolltop[this.channel.id];
            this.thread.scroll_to({offset: newChannelScrolltop});
        }
        this._restoreComposerState(this.channel);
    },
    /**
     * @private
     * @param {Object} channel
     */
    _restoreComposerState: function (channel) {
        if (channel.type === 'static') {
            return; // no composer in static channels
        }
        var composer = channel.mass_mailing ? this.extendedComposer : this.basicComposer;
        var composerState = this.composerStates[channel.uuid];
        if (composerState) {
            composer.setState(composerState);
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
                    var escaped_name = _.escape(channel.name);
                    values.push(_.extend(channel, {
                        'value': escaped_name,
                        'label': escaped_name,
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
        var message = this.call('chat_manager', 'getMessage', messageID);;
        this.selected_message = message;
        var subject = "Re: " + message.record_name;
        this.extendedComposer.set_subject(subject);

        if (this.channel.type !== 'static') {
            this.basicComposer.do_hide();
        }
        this.extendedComposer.do_show();

        this.thread.scroll_to({id: messageID, duration: 200, only_if_necessary: true});
        this.extendedComposer.focus('body');
    },
    /**
     * @private
     * @param {Object} channel
     * @returns {$.Promise}
     */
    _setChannel: function (channel) {
        var self = this;

        // Store scroll position and composer state of the previous channel
        this._storeChannelState();

        this.channel = channel;
        this.messages_separator_position = undefined; // reset value on channel change
        this.unread_counter = this.channel.unread_counter;
        this.last_seen_message_id = this.channel.last_seen_message_id;
        if (this.$snackbar) {
            this.$snackbar.remove();
        }

        this.action.context.active_id = channel.id;
        this.action.context.active_ids = [channel.id];

        return this._fetchAndRenderThread().then(function () {
            // Mark channel's messages as read and clear needactions
            if (channel.type !== 'static') {
                self.call('chat_manager', 'markChannelAsSeen', channel);
            }
            // Restore scroll position and composer of the new current channel
            self._restoreChannelState();

            // Update control panel before focusing the composer, otherwise focus is on the searchview
            self.set("title", '#' + channel.name);
            self._updateControlPanel();
            self._updateControlPanelButtons(channel);

            // Display and focus the adequate composer, and unselect possibly selected message
            // to prevent sending messages as reply to that message
            self._unselectMessage();

            self.action_manager.do_push_state({
                action: self.action.id,
                active_id: self.channel.id,
            });
        });
    },
    /**
     * Binds handlers on chatManager events
     *
     * @private
     */
    _startListening: function () {
        var chatBus = this.call('chat_manager', 'getChatBus');
        chatBus.on('open_channel', this, this._setChannel);
        chatBus.on('new_message', this, this._onNewMessage);
        chatBus.on('update_message', this, this._onMessageUpdated);
        chatBus.on('new_channel', this, this._onNewChannel);
        chatBus.on('anyone_listening', this, function (channel, query) {
            query.is_displayed = query.is_displayed ||
                                (channel.id === this.channel.id && this.thread.is_at_bottom());
        });
        chatBus.on('unsubscribe_from_channel', this, this._onChannelLeft);
        chatBus.on('update_needaction', this, this.throttledUpdateChannels);
        chatBus.on('update_starred', this, this.throttledUpdateChannels);
        chatBus.on('update_channel_unread_counter', this, this.throttledUpdateChannels);
        chatBus.on('update_dm_presence', this, this.throttledUpdateChannels);
        chatBus.on('activity_updated', this, this.throttledUpdateChannels);
        chatBus.on('update_moderation_counter', this, this.throttledUpdateChannels);
    },
    /**
     * Stores the scroll position and composer state of the current channel
     *
     * @private
     */
    _storeChannelState: function () {
        if (this.channel) {
            this.channelsScrolltop[this.channel.id] = this.thread.get_scrolltop();
            this._storeComposerState(this.channel);
        }
    },
    /**
     * @private
     * @param {Object} channel
     */
    _storeComposerState: function (channel) {
        if (channel.type === 'static') {
            return; // no composer in static channels
        }
        var composer = channel.mass_mailing ? this.extendedComposer : this.basicComposer;
        this.composerStates[channel.uuid] = composer.getState();
        composer.clear_composer();
    },
    /**
     * @private
     */
    _unselectMessage: function () {
        this.basicComposer.do_toggle(this.channel.type !== 'static' && !this.channel.mass_mailing);
        this.extendedComposer.do_toggle(this.channel.type !== 'static' && !!this.channel.mass_mailing);

        if (!config.device.touch) {
            var composer = this.channel.mass_mailing ? this.extendedComposer : this.basicComposer;
            composer.focus();
        }
        this.$el.removeClass('o_mail_selection_mode');
        this.thread.unselect();
        this.selected_message = null;
    },
    /**
     * Renders the mainside bar with current channels
     *
     * @private
     */
    _updateChannels: function () {
        var self = this;
        var $sidebar = this._renderSidebar({
            active_channel_id: this.channel ? this.channel.id: undefined,
            channels: this.call('chat_manager', 'getChannels'),
            needaction_counter: this.call('chat_manager', 'getNeedactionCounter'),
            starred_counter: this.call('chat_manager', 'getStarredCounter'),
            moderationCounter: this.call('chat_manager', 'getModerationCounter'),
            isModerator: this.call('chat_manager', 'isModerator'),
        });
        this.$(".o_mail_chat_sidebar").html($sidebar.contents());
        _.each(['dm', 'public', 'private'], function (type) {
            var $input = self.$('.o_mail_add_channel[data-type=' + type + '] input');
            self._prepareAddChannelInput($input, type);
        });
    },
    /**
     * @private
     * @param {boolean} disabled
     * @param {string} type
     */
    _updateButtonStatus: function (disabled, type) {
        if (this.channel.id === "channel_inbox") {
            this.$buttons
                .find('.o_mail_chat_button_mark_read')
                .toggleClass('disabled', disabled);
            // Display Rainbowman when all inbox messages are read through
            // 'MARK ALL READ' or marking last inbox message as read
            if (disabled && type === 'mark_as_read') {
                this.trigger_up('show_effect', {
                    message: _t('Congratulations, your inbox is empty!'),
                    type: 'rainbow_man',
                });
            }
        }
        if (this.channel.id === "channel_starred") {
            this.$buttons
                .find('.o_mail_chat_button_unstar_all')
                .toggleClass('disabled', disabled);
        }
        if ((this.channel.isModerated && this.channel.isModerator) || this.channel.id === "channel_moderation") {
            this._updateModerationButtons();
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
     * Updates the control panel buttons visibility based on channel type
     *
     * @private
     * @param {Object} channel
     */
    _updateControlPanelButtons: function (channel) {
        // Hide 'unsubscribe' button in state channels and DM and channels with group-based subscription
        this.$buttons
            .find('.o_mail_chat_button_invite, .o_mail_chat_button_settings')
            .toggle(channel.type !== "dm" && channel.type !== 'static');
        this.$buttons
            .find('.o_mail_chat_button_mark_read')
            .toggle(channel.id === "channel_inbox")
            .removeClass("o_hidden");
        this.$buttons
            .find('.o_mail_chat_button_unstar_all')
            .toggle(channel.id === "channel_starred")
            .removeClass("o_hidden");
        this.$buttons
            .find('.o_mail_chat_button_select_all')
            .toggle((channel.isModerated && channel.isModerator) || channel.id === "channel_moderation")
            .removeClass("o_hidden");
        this.$buttons
            .find('.o_mail_chat_button_unselect_all')
            .toggle((channel.isModerated && channel.isModerator) || channel.id === "channel_moderation")
            .removeClass("o_hidden");
        this.$buttons.find('.o_mail_chat_button_moderate_all').hide();
        this.$('.o_mail_chat_channel_item')
            .removeClass('o_active')
            .filter('[data-channel-id=' + channel.id + ']')
            .removeClass('o_unread_message')
            .addClass('o_active');
    },
    /**
     * Update the moderation buttons.
     *
     * @private
     */
    _updateModerationButtons: function () {
        this._updateSelectUnselectAllButtons();
        this._updateModerationDecisionButton();
    },
    /**
     * Display/hide the "moderate all" button based on whether
     * some moderation checkboxes are checked or not.
     * If some checkboxes are checked, display this button,
     * otherwise hide it.
     *
     * @private
     */
    _updateModerationDecisionButton: function () {
        if (this.thread.$('.moderation_checkbox:checked').length) {
            this.$buttons.find('.o_mail_chat_button_moderate_all').show();
        } else {
            this.$buttons.find('.o_mail_chat_button_moderate_all').hide();
        }
    },
    /**
     * @private
     */
    _updateSelectUnselectAllButtons: function () {
        var buttonSelect = this.$buttons.find('.o_mail_chat_button_select_all');
        var buttonUnselect = this.$buttons.find('.o_mail_chat_button_unselect_all');
        var numCheckboxes = this.thread.$('.moderation_checkbox').length;
        var numCheckboxesChecked = this.thread.$('.moderation_checkbox:checked').length;
        if (numCheckboxes) {
            if (numCheckboxesChecked === numCheckboxes) {
                buttonSelect.toggleClass('disabled', true);
                buttonUnselect.toggleClass('disabled', false);
            } else if (numCheckboxesChecked === 0) {
                buttonSelect.toggleClass('disabled', false);
                buttonUnselect.toggleClass('disabled', true);
            } else {
                buttonSelect.toggleClass('disabled', false);
                buttonUnselect.toggleClass('disabled', false);
            }
        } else {
            buttonSelect.toggleClass('disabled', true);
            buttonUnselect.toggleClass('disabled', true);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddChannel: function (event) {
        event.preventDefault();
        var type = $(event.target).data("type");
        this.$('.o_mail_add_channel[data-type=' + type + ']')
            .show()
            .find("input").focus();
    },
    /**
     * @private
     */
    _onAddChannelBlur: function () {
        this.$('.o_mail_add_channel').hide();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onChannelClicked: function (event) {
        event.preventDefault();
        var channelID = $(event.currentTarget).data('channel-id');
        var channel = this.call('chat_manager', 'getChannel', channelID);
        this._setChannel(channel);
    },
    /**
     * @private
     * @param {integer|string} channelID
     */
    _onChannelLeft: function (channelID) {
        if (this.channel.id === channelID) {
            var channel = this.call('chat_manager', 'getChannel', 'channel_inbox');
            this._setChannel(channel);
        }
        this._updateChannels();
        delete this.channelsScrolltop[channelID];
    },
    /**
     * @private
     */
    _onCloseNotificationBar: function () {
        this.$(".o_mail_annoying_notification_bar").slideUp();
    },
    /**
     * @private
     */
    _onComposerFocused: function () {
        var composer = this.channel.mass_mailing ? this.extendedComposer : this.basicComposer;
        var commands = this.call('chat_manager', 'getCommands', this.channel);
        var partners = this.call('chat_manager', 'getMentionPartnerSuggestions', this.channel);
        composer.mention_set_enabled_commands(commands);
        composer.mention_set_prefetched_partners(partners);
    },
    /**
     * @private
     */
    _onInviteButtonClicked: function () {
        var title = _.str.sprintf(_t('Invite people to #%s'), this.channel.name);
        new PartnerInviteDialog(this, title, this.channel.id).open();
    },
    /**
     * @private
     * @param {KeyEvent} event
     */
    _onKeydown: function (event) {
        if (event.which === $.ui.keyCode.ESCAPE && this.selected_message) {
            this._unselectMessage();
        }
    },
    /**
     * @private
     */
    _onMarkAllReadClicked: function () {
        this.call('chat_manager', 'markAllAsRead', this.channel, this.domain);
    },
    /**
     * @private
     * @param {Object} message
     * @param {string} type the channel type
     */
    _onMessageUpdated: function (message, type) {
        var self = this;
        var currentChannelID = this.channel.id;
        if ((currentChannelID === "channel_starred" && !message.is_starred) ||
            (currentChannelID === "channel_moderation" && !message.needsModeration) ||
            (currentChannelID === "channel_inbox" && !message.is_needaction)) {
                this.call('chat_manager', 'getMessages', {
                        channelID: this.channel.id,
                        domain: this.domain
                }).then(function (messages) {
                    var options = self._getThreadRenderingOptions(messages);
                    self.thread.remove_message_and_render(message.id, messages, options)
                        .then(function () {
                            self._updateButtonStatus(messages.length === 0, type);
                        });
                });
        } else if (_.contains(message.channel_ids, currentChannelID) || (message.res_id === currentChannelID)) {
            this._fetchAndRenderThread();
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onModerateAllClicked: function (ev) {
        var decision = $(ev.target).data('decision');
        var messageIDs = this.thread.$('.moderation_checkbox:checked')
                            .map(function () {
                                return $(this).data('message-id');
                            })
                            .get();
        this._handleModerationDecision(messageIDs, decision);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.messageID ID of the moderated message
     * @param {string} ev.data.decision can be 'reject', 'discard', 'ban', 'accept', 'allow'.
     */
    _onMessageModeration: function (ev) {
        var messageIDs = [ev.data.messageID];
        var decision = ev.data.decision;
        this._handleModerationDecision(messageIDs, decision);
    },
    /**
     * @private
     * @param {Object} channel
     */
    _onNewChannel: function (channel) {
        this._updateChannels();
        if (channel.autoswitch) {
            this._setChannel(channel);
        }
    },
    /**
     * @private
     * @param {Object} message
     */
    _onNewMessage: function (message) {
        var self = this;
        if (_.contains(message.channel_ids, this.channel.id)) {
            if (this.channel.type !== 'static' && this.thread.is_at_bottom()) {
                this.call('chat_manager', 'markChannelAsSeen', this.channel);
            }
            var should_scroll = this.thread.is_at_bottom();
            this._fetchAndRenderThread().then(function () {
                if (should_scroll) {
                    self.thread.scroll_to({id: message.id});
                }
            });
        }
        // Re-render sidebar to indicate that there is a new message in the corresponding channels
        this._updateChannels();
        // Dump scroll position of channels in which the new message arrived
        this.channelsScrolltop = _.omit(this.channelsScrolltop, message.channel_ids);
    },
    /**
     * @private
     * @param {Object} message
     */
    _onPostMessage: function (message) {
        var self = this;
        var options = this.selected_message ? {} : {channelID: this.channel.id};
        if (this.selected_message) {
            message.subtype = this.selected_message.is_note ? 'mail.mt_note': 'mail.mt_comment';
            message.subtype_id = false;
            message.message_type = 'comment';
        }
        this.call('chat_manager', 'postMessage', message, options)
            .then(function () {
                if (self.selected_message) {
                    self._renderSnackbar('mail.chat.MessageSentSnackbar', {record_name: self.selected_message.record_name}, 5000);
                    self._unselectMessage();
                } else {
                    self.thread.scroll_to();
                }
            })
            .fail(function () {
                // todo: display notifications
            });
    },
    /**
     * @private
     */
    _onPublicChannelsClick: function () {
        this.do_action({
            name: _t('Public Channels'),
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            views: [[false, 'kanban'], [false, 'form']],
            domain: [['public', '!=', 'private']],
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onRequestNotificationPermission: function (event) {
        var self = this;
        event.preventDefault();
        this.$(".o_mail_annoying_notification_bar").slideUp();
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then(function (value) {
                if (value !== 'granted') {
                    self.call('bus_service', 'sendNotification', self, _t('Permission denied'),
                        _t('Odoo will not have the permission to send native notifications on this device.'));
                } else {
                    self.call('bus_service', 'sendNotification', self, _t('Permission granted'),
                        _t('Odoo has now the permission to send you native notifications on this device.'));
                }
            });
        }
    },
    /**
     * @private
     * @param {OdooEvent}
     */
    _onSearch: function (event) {
        event.stopPropagation();
        var session = this.getSession();
        var result = pyeval.eval_domains_and_contexts({
            domains: event.data.domains,
            contexts: [session.user_context],
        });
        this.domain = result.domain;
        if (this.channel) {
            // initially (when _onSearch is called manually), there is no
            // channel set yet, so don't try to fetch and render the thread as
            // this will be done as soon as the default channel is set
            this._fetchAndRenderThread();
        }
    },
     /**
     * @private
     * @param {MouseEvent} ev
     */
    _onSelectAllClicked: function (ev) {
        var $button = $(ev.target);
        if (!$button.hasClass('disabled')) {
            this.thread.toggleModerationCheckboxes(true);
            this._updateModerationButtons();
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onChannelSettingsClicked: function (event) {
        var channelID = $(event.target).data("channel-id");
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            res_id: channelID,
            views: [[false, 'form']],
            target: 'current'
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onUnpinChannel: function (event) {
        event.stopPropagation();
        var channelID = $(event.target).data("channel-id");
        var channel = this.call('chat_manager', 'getChannel', channelID);
        this.call('chat_manager', 'unsubscribe', channel);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onUnselectAllClicked: function (ev) {
        var $button = $(ev.target);
        if (!$button.hasClass('disabled')) {
            this.thread.toggleModerationCheckboxes(false);
            this._updateModerationButtons();
        }
    },
    /**
     * @private
     */
    _onUnstarAllClicked: function () {
        this.call('chat_manager', 'unstarAll');
    },
    /**
     * Update the moderation buttons.
     * This is triggered when a moderation checkbox
     * has its checked property changed.
     *
     * @private
     */
    _onUpdateModerationButtons: function () {
        this._updateModerationButtons();
    },
});

core.action_registry.add('mail.chat.instant_messaging', Discuss);

return Discuss;

});
