odoo.define('mail.chat_client_action', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatThread = require('mail.ChatThread');
var composer = require('mail.composer');
var utils = require('mail.utils');

var config = require('web.config');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var session = require('web.session');
var Widget = require('web.Widget');

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
     */
    init: function (parent, title, channel_id) {
        this.channel_id = channel_id;

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
    start: function (){
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
                chat_manager.search_partner(query.term, 20).then(function (partners) {
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
     * @returns {Deferred}
     */
    _addChannel: function () {
        var self = this;
        var data = this.$input.select2('data');
        if (data.length >= 1) {
            return this._rpc({
                    model: 'mail.channel',
                    method: 'channel_invite',
                    args: [this.channel_id],
                    kwargs: {partner_ids: _.pluck(data, 'id')},
                }).then(function () {
                    var names = _.escape(_.pluck(data, 'text').join(', '));
                    var notification = _.str.sprintf(_t('You added <b>%s</b> to the conversation.'), names);
                    self.do_notify(_t('New people'), notification);
                    // Clear the members_deferred to fetch again the partner
                    // when get_mention_partner_suggestions from the chat_manager is triggered
                    delete chat_manager.get_channel(self.channel_id).members_deferred;
                });
        }
    },
});

var ChatAction = Widget.extend(ControlPanelMixin, {
    template: 'mail.client_action',
    custom_events: {
        search: '_onSearch',
    },
    events: {
        'blur .o_mail_add_channel input': '_onAddChannelBlur',
        'click .o_mail_annoying_notification_bar .fa-close': '_onCloseNotificationBar',
        'click .o_mail_chat_channel_item': '_onChannelClicked',
        'click .o_mail_open_channels': '_onPublicChannelsClick',
        'click .o_mail_partner_unpin': '_onUnpinChannel',
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
        this.channels_scrolltop = {};
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
        var view_id = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = this
            .loadFieldView(this.dataset, view_id, 'search')
            .then(function (fields_view) {
                self.fields_view = fields_view;
            });
        return $.when(this._super(), chat_manager.is_ready, def);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        var default_channel = chat_manager.get_channel(this.defaultChannelID) ||
                              chat_manager.get_channel('channel_inbox');
        this.basic_composer = new composer.BasicComposer(this, {mention_partners_restricted: true});
        this.extended_composer = new composer.ExtendedComposer(this, {mention_partners_restricted: true});
        this.basic_composer.on('post_message', this, this._onPostMessage);
        this.basic_composer.on('input_focused', this, this._onComposerFocused);
        this.extended_composer.on('post_message', this, this._onPostMessage);
        this.extended_composer.on('input_focused', this, this._onComposerFocused);

        var defs = [];
        defs.push(this._renderButtons());
        defs.push(this._renderThread());
        defs.push(this.basic_composer.appendTo(this.$('.o_mail_chat_content')));
        defs.push(this.extended_composer.appendTo(this.$('.o_mail_chat_content')));
        defs.push(this._renderSearchView());

        return $.when.apply($, defs)
            .then(this._setChannel.bind(this, default_channel))
            .then(this._updateChannels.bind(this))
            .then(function () {
                self._startListening();
                self.thread.$el.on("scroll", null, _.debounce(function () {
                    if (self.thread.is_at_bottom()) {
                        chat_manager.mark_channel_as_seen(self.channel);
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
        chat_manager.bus.trigger('client_action_open', true);
        if (this.channel) {
            this.thread.scroll_to({offset: this.channels_scrolltop[this.channel.id]});
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        chat_manager.bus.trigger('client_action_open', false);
        this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Deferred}
     */
    _fetchAndRenderThread: function () {
        var self = this;
        return chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function (result) {
            self.thread.render(result, self._getThreadRenderingOptions(result));
            self._updateButtonStatus(result.length === 0);
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
                var msg = chat_manager.get_last_seen_message(this.channel);
                this.messages_separator_position = msg ? msg.id : 'top';
            }
        }
        return {
            channel_id: this.channel.id,
            display_load_more: !chat_manager.all_history_loaded(this.channel, this.domain),
            display_needactions: this.channel.display_needactions,
            messages_separator_position: this.messages_separator_position,
            squash_close_messages: this.channel.type !== 'static' && !this.channel.mass_mailing,
            display_empty_channel: !messages.length && !this.domain.length,
            display_no_match: !messages.length && this.domain.length,
            display_subject: this.channel.mass_mailing || this.channel.id === "channel_inbox",
            display_email_icon: false,
            display_reply_icon: true,
        };
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _loadMoreMessages: function () {
        var self = this;
        var oldest_msg_id = this.$('.o_thread_message').first().data('messageId');
        var oldest_msg_selector = '.o_thread_message[data-message-id="' + oldest_msg_id + '"]';
        var offset = -dom.getPosition(document.querySelector(oldest_msg_selector)).top;
        return chat_manager
            .get_messages({channel_id: this.channel.id, domain: this.domain, load_more: true})
            .then(function (result) {
                if (self.messages_separator_position === 'top') {
                    self.messages_separator_position = undefined; // reset value to re-compute separator position
                }
                self.thread.render(result, self._getThreadRenderingOptions(result));
                offset += dom.getPosition(document.querySelector(oldest_msg_selector)).top;
                self.thread.scroll_to({offset: offset});
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
                            chat_manager.create_channel(self.last_search_val, "public");
                        } else {
                            chat_manager.join_channel(ui.item.id);
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
                if(event.which === $.ui.keyCode.ENTER && name) {
                    chat_manager.create_channel(name, "private");
                }
            });
        } else if (type === 'dm') {
            $input.autocomplete({
                source: function (request, response) {
                    self.last_search_val = _.escape(request.term);
                    chat_manager.search_partner(self.last_search_val, 10).done(response);
                },
                select: function (event, ui) {
                    var partner_id = ui.item.id;
                    var dm = chat_manager.get_dm_from_partner_id(partner_id);
                    if (dm) {
                        self._setChannel(dm);
                    } else {
                        chat_manager.create_channel(partner_id, "dm");
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
     * @private
     */
    _renderButtons: function () {
        this.$buttons = $(QWeb.render("mail.chat.ControlButtons", {debug: session.debug}));
        this.$buttons.find('button').css({display:"inline-block"});
        this.$buttons.on('click', '.o_mail_chat_button_invite', this._onInviteButtonClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_unsubscribe', this._onUnsubscribeButtonClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_settings', this._onSettingsButtonClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_mark_read', this._onMarkAllReadClicked.bind(this));
        this.$buttons.on('click', '.o_mail_chat_button_unstar_all', this._onUnstarAllClicked.bind(this));
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
        return this.searchview.appendTo($("<div>")).then(function () {
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
        this.thread = new ChatThread(this, {display_help: true});

        this.thread.on('redirect', this, function (res_model, res_id) {
            chat_manager.redirect(res_model, res_id, this._setChannel.bind(this));
        });
        this.thread.on('redirect_to_channel', this, function (channel_id) {
            chat_manager.join_channel(channel_id).then(this._setChannel.bind(this));
        });
        this.thread.on('load_more_messages', this, this._loadMoreMessages);
        this.thread.on('mark_as_read', this, function (message_id) {
            chat_manager.mark_as_read([message_id]);
        });
        this.thread.on('toggle_star_status', this, function (message_id) {
            chat_manager.toggle_star_status(message_id);
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
        var $new_messages_separator = this.$('.o_thread_new_messages_separator');
        if ($new_messages_separator.length) {
            this.thread.$el.scrollTo($new_messages_separator);
        } else {
            var new_channel_scrolltop = this.channels_scrolltop[this.channel.id];
            this.thread.scroll_to({offset: new_channel_scrolltop});
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
        var composer = channel.mass_mailing ? this.extended_composer : this.basic_composer;
        var composerState = this.composerStates[channel.uuid];
        if (composerState) {
            composer.setState(composerState);
        }
    },
    /**
     * @private
     * @param {string} search_val
     * @returns {Deferred<Array>}
     */
    _searchChannel: function (search_val){
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_search_to_join',
                args: [search_val]
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
     * @param {integer} message_id
     */
    _selectMessage: function (message_id) {
        this.$el.addClass('o_mail_selection_mode');
        var message = chat_manager.get_message(message_id);
        this.selected_message = message;
        var subject = "Re: " + message.record_name;
        this.extended_composer.set_subject(subject);

        if (this.channel.type !== 'static') {
            this.basic_composer.do_hide();
        }
        this.extended_composer.do_show();

        this.thread.scroll_to({id: message_id, duration: 200, only_if_necessary: true});
        this.extended_composer.focus('body');
    },
    /**
     * @private
     * @param {Object} channel
     * @returns {Deferred}
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
                chat_manager.mark_channel_as_seen(channel);
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
     * Binds handlers on chat_manager events
     *
     * @private
     */
    _startListening: function () {
        chat_manager.bus.on('open_channel', this, this._setChannel);
        chat_manager.bus.on('new_message', this, this._onNewMessage);
        chat_manager.bus.on('update_message', this, this._onMessageUpdated);
        chat_manager.bus.on('new_channel', this, this._onNewChannel);
        chat_manager.bus.on('anyone_listening', this, function (channel, query) {
            query.is_displayed = query.is_displayed ||
                                 (channel.id === this.channel.id && this.thread.is_at_bottom());
        });
        chat_manager.bus.on('unsubscribe_from_channel', this, this._onChannelLeft);
        chat_manager.bus.on('update_needaction', this, this.throttledUpdateChannels);
        chat_manager.bus.on('update_starred', this, this.throttledUpdateChannels);
        chat_manager.bus.on('update_channel_unread_counter', this, this.throttledUpdateChannels);
        chat_manager.bus.on('update_dm_presence', this, this.throttledUpdateChannels);
        chat_manager.bus.on('activity_updated', this, this.throttledUpdateChannels);
    },
    /**
     * Stores the scroll position and composer state of the current channel
     *
     * @private
     */
    _storeChannelState: function () {
        if (this.channel) {
            this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
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
        var composer = channel.mass_mailing ? this.extended_composer : this.basic_composer;
        this.composerStates[channel.uuid] = composer.getState();
        composer.clear_composer();
    },
    /**
     * @private
     */
    _unselectMessage: function () {
        this.basic_composer.do_toggle(this.channel.type !== 'static' && !this.channel.mass_mailing);
        this.extended_composer.do_toggle(this.channel.type !== 'static' && this.channel.mass_mailing);

        if (!config.device.touch) {
            var composer = this.channel.mass_mailing ? this.extended_composer : this.basic_composer;
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
            channels: chat_manager.get_channels(),
            needaction_counter: chat_manager.get_needaction_counter(),
            starred_counter: chat_manager.get_starred_counter(),
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
    },
    /**
     * @private
     */
    _updateControlPanel: function () {
        this.update_control_panel({
            breadcrumbs: this.action_manager.get_breadcrumbs(),
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
            .find('.o_mail_chat_button_unsubscribe')
            .toggle(channel.type !== "dm" && channel.type !== 'static' && ! channel.group_based_subscription);
        // Hide 'invite', 'unsubscribe' and 'settings' buttons in static channels and DM
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

        this.$('.o_mail_chat_channel_item')
            .removeClass('o_active')
            .filter('[data-channel-id=' + channel.id + ']')
            .removeClass('o_unread_message')
            .addClass('o_active');
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
        var channel_id = $(event.currentTarget).data('channel-id');
        this._setChannel(chat_manager.get_channel(channel_id));
    },
    /**
     * @private
     * @param {integer || string} channel_id
     */
    _onChannelLeft: function (channel_id) {
        if (this.channel.id === channel_id) {
            this._setChannel(chat_manager.get_channel("channel_inbox"));
        }
        this._updateChannels();
        delete this.channels_scrolltop[channel_id];
    },
    /**
     * @private
     */
    _onComposerFocused: function () {
        var composer = this.channel.mass_mailing ? this.extended_composer : this.basic_composer;
        var commands = chat_manager.get_commands(this.channel);
        var partners = chat_manager.get_mention_partner_suggestions(this.channel);
        composer.mention_set_enabled_commands(commands);
        composer.mention_set_prefetched_partners(partners);
    },
    /**
     * @private
     */
    _onMarkAllReadClicked: function () {
        chat_manager.mark_all_as_read(this.channel, this.domain);
    },
    /**
     * @private
     * @param {Object} message
     * @param {string} type the channel type
     */
    _onMessageUpdated: function (message, type) {
        var self = this;
        var current_channel_id = this.channel.id;
        if ((current_channel_id === "channel_starred" && !message.is_starred) ||
            (current_channel_id === "channel_inbox" && !message.is_needaction)) {
            chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function (messages) {
                var options = self._getThreadRenderingOptions(messages);
                self.thread.remove_message_and_render(message.id, messages, options).then(function () {
                    self._updateButtonStatus(messages.length === 0, type);
                });
            });
        } else if (_.contains(message.channel_ids, current_channel_id)) {
            this._fetchAndRenderThread();
        }
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
                chat_manager.mark_channel_as_seen(this.channel);
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
        this.channels_scrolltop = _.omit(this.channels_scrolltop, message.channel_ids);
    },
    /**
     * @private
     * @param {Object} message
     */
    _onPostMessage: function (message) {
        var self = this;
        var options = this.selected_message ? {} : {channel_id: this.channel.id};
        if (this.selected_message) {
            message.subtype = this.selected_message.is_note ? 'mail.mt_note': 'mail.mt_comment';
            message.subtype_id = false;
            message.message_type = 'comment';
            message.content_subtype = 'html';

            options.model = this.selected_message.model;
            options.res_id = this.selected_message.res_id;
        }
        chat_manager
            .post_message(message, options)
            .then(function () {
                if (self.selected_message) {
                    self._renderSnackbar('mail.chat.MessageSentSnackbar', {record_name: self.selected_message.record_name}, 5000);
                    self._unselectMessage();
                } else {
                    self.thread.scroll_to();
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
     */
    _onCloseNotificationBar: function () {
        this.$(".o_mail_annoying_notification_bar").slideUp();
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
     * @param {MouseEvent} event
     */
    _onRequestNotificationPermission: function (event) {
        var self = this;
        event.preventDefault();
        this.$(".o_mail_annoying_notification_bar").slideUp();
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then(function (value) {
                if (value === 'denied') {
                    utils.send_notification(self, _t('Permission denied'),
                        _t('Odoo will not have the permission to send native notifications on this device.'));
                } else {
                    utils.send_notification(self, _t('Permission granted'),
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
     */
    _onSettingsButtonClicked: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            res_id: this.channel.id,
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
        var channel_id = $(event.target).data("channel-id");
        chat_manager.unsubscribe(chat_manager.get_channel(channel_id));
    },
    /**
     * @private
     */
    _onUnstarAllClicked: function () {
        chat_manager.unstar_all();
    },
    /**
     * @private
     */
    _onUnsubscribeButtonClicked: function () {
        chat_manager.unsubscribe(this.channel);
    },
});

core.action_registry.add('mail.chat.instant_messaging', ChatAction);

return ChatAction;

});
