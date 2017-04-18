odoo.define('mail.chat_client_action', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var ChatThread = require('mail.ChatThread');
var utils = require('mail.utils');

var config = require('web.config');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Model = require('web.Model');

var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Widget : Invite People to Channel Dialog
 *
 * Popup containing a 'many2many_tags' custom input to select multiple partners.
 * Search user according to the input, and trigger event when selection is validated.
 **/
var PartnerInviteDialog = Dialog.extend({
    dialog_title: _t('Invite people'),
    template: "mail.PartnerInviteDialog",
    init: function(parent, title, channel_id){
        this.channel_id = channel_id;

        this._super(parent, {
            title: title,
            size: "medium",
            buttons: [{
                text: _t("Invite"),
                close: true,
                classes: "btn-primary",
                click: _.bind(this.on_click_add, this),
            }],
        });
    },
    start: function(){
        this.$input = this.$('.o_mail_chat_partner_invite_input');
        this.$input.select2({
            width: '100%',
            allowClear: true,
            multiple: true,
            formatResult: function(item) {
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
    on_click_add: function(){
        var self = this;
        var data = this.$input.select2('data');
        if(data.length >= 1){
            var ChannelModel = new Model('mail.channel');
            return ChannelModel.call('channel_invite', [this.channel_id], {partner_ids: _.pluck(data, 'id')})
                .then(function(){
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

    events: {
        "click .o_mail_chat_channel_item": function (event) {
            event.preventDefault();
            var channel_id = this.$(event.currentTarget).data('channel-id');
            this.set_channel(chat_manager.get_channel(channel_id));
        },
        "click .o_mail_sidebar_title .o_add": function (event) {
            event.preventDefault();
            var type = $(event.target).data("type");
            this.$('.o_mail_add_channel[data-type=' + type + ']')
                .show()
                .find("input").focus();
        },
        "blur .o_mail_add_channel input": function () {
            this.$('.o_mail_add_channel')
                .hide();
        },
        "click .o_mail_partner_unpin": function (event) {
            event.stopPropagation();
            var channel_id = $(event.target).data("channel-id");
            chat_manager.unsubscribe(chat_manager.get_channel(channel_id));
        },
        "click .o_mail_annoying_notification_bar .fa-close": function () {
            this.$(".o_mail_annoying_notification_bar").slideUp();
        },
        "click .o_mail_request_permission": function (event) {
            event.preventDefault();
            this.$(".o_mail_annoying_notification_bar").slideUp();
            var def = window.Notification && window.Notification.requestPermission();
            if (def) {
                def.then(function (value) {
                    if (value === 'denied') {
                        utils.send_notification(_t('Permission denied'), _t('Odoo will not have the permission to send native notifications on this device.'));
                    } else {
                        utils.send_notification(_t('Permission granted'), _t('Odoo has now the permission to send you native notifications on this device.'));
                    }
                });
            }
        },
        "keydown": function (event) {
            if (event.which === $.ui.keyCode.ESCAPE && this.selected_message) {
                this.unselect_message();
            }
        },
        "click .o_mail_open_channels": function () {
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
    },

    on_attach_callback: function () {
        chat_manager.bus.trigger('client_action_open', true);
        if (this.channel) {
            this.thread.scroll_to({offset: this.channels_scrolltop[this.channel.id]});
        }
    },
    on_detach_callback: function () {
        chat_manager.bus.trigger('client_action_open', false);
        this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
    },

    init: function(parent, action, options) {
        this._super.apply(this, arguments);
        this.action_manager = parent;
        this.dataset = new data.DataSetSearch(this, 'mail.message');
        this.domain = [];
        this.action = action;
        this.options = options || {};
        this.channels_scrolltop = {};
        this.throttled_render_sidebar = _.throttle(this.render_sidebar.bind(this), 100, { leading: false });
        this.notification_bar = (window.Notification && window.Notification.permission === "default");
        this.selected_message = null;
    },

    willStart: function () {
        var self = this;
        var view_id = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = data_manager
            .load_fields_view(this.dataset, view_id, 'search', false)
            .then(function (fields_view) {
                self.fields_view = fields_view;
            });
        return $.when(this._super(), chat_manager.is_ready, def);
    },

    start: function() {
        var self = this;

        // create searchview
        var options = {
            $buttons: $("<div>"),
            action: this.action,
            disable_groupby: true,
        };
        var default_channel_id = this.options.active_id ||
                                 this.action.context.active_id ||
                                 this.action.params.default_active_id ||
                                 'channel_inbox';
        var default_channel = chat_manager.get_channel(default_channel_id) ||
                              chat_manager.get_channel('channel_inbox');

        this.searchview = new SearchView(this, this.dataset, this.fields_view, options);
        this.searchview.on('search_data', this, this.on_search);

        this.basic_composer = new composer.BasicComposer(this, {mention_partners_restricted: true});
        this.extended_composer = new composer.ExtendedComposer(this, {mention_partners_restricted: true});
        this.thread = new ChatThread(this, {
            display_help: true,
        });

        this.$buttons = $(QWeb.render("mail.chat.ControlButtons", {}));
        this.$buttons.find('button').css({display:"inline-block"});
        this.$buttons.on('click', '.o_mail_chat_button_invite', this.on_click_button_invite);
        this.$buttons.on('click', '.o_mail_chat_button_unsubscribe', this.on_click_button_unsubscribe);
        this.$buttons.on('click', '.o_mail_chat_button_settings', this.on_click_button_settings);
        this.$buttons.on('click', '.o_mail_toggle_channels', function () {
            self.$('.o_mail_chat_sidebar').slideToggle(200);
        });
        this.$buttons.on('click', '.o_mail_chat_button_mark_read', function () {
            chat_manager.mark_all_as_read(self.channel, self.domain);
        });
        this.$buttons.on('click', '.o_mail_chat_button_unstar_all', chat_manager.unstar_all);

        this.thread.on('redirect', this, function (res_model, res_id) {
            chat_manager.redirect(res_model, res_id, this.set_channel.bind(this));
        });
        this.thread.on('redirect_to_channel', this, function (channel_id) {
            chat_manager.join_channel(channel_id).then(this.set_channel.bind(this));
        });
        this.thread.on('load_more_messages', this, this.load_more_messages);
        this.thread.on('mark_as_read', this, function (message_id) {
            chat_manager.mark_as_read([message_id]);
        });
        this.thread.on('toggle_star_status', this, function (message_id) {
            chat_manager.toggle_star_status(message_id);
        });
        this.thread.on('select_message', this, this.select_message);
        this.thread.on('unselect_message', this, this.unselect_message);

        this.basic_composer.on('post_message', this, this.on_post_message);
        this.basic_composer.on('input_focused', this, this.on_composer_input_focused);
        this.extended_composer.on('post_message', this, this.on_post_message);
        this.extended_composer.on('input_focused', this, this.on_composer_input_focused);

        var def1 = this.thread.appendTo(this.$('.o_mail_chat_content'));
        var def2 = this.basic_composer.appendTo(this.$('.o_mail_chat_content'));
        var def3 = this.extended_composer.appendTo(this.$('.o_mail_chat_content'));
        var def4 = this.searchview.appendTo($("<div>")).then(function () {
            self.$searchview_buttons = self.searchview.$buttons.contents();
        });

        this.render_sidebar();

        return $.when(def1, def2, def3, def4)
            .then(this.set_channel.bind(this, default_channel))
            .then(function () {
                chat_manager.bus.on('open_channel', self, self.set_channel);
                chat_manager.bus.on('new_message', self, self.on_new_message);
                chat_manager.bus.on('update_message', self, self.on_update_message);
                chat_manager.bus.on('new_channel', self, self.on_new_channel);
                chat_manager.bus.on('anyone_listening', self, function (channel, query) {
                    query.is_displayed = query.is_displayed || (channel.id === self.channel.id && self.thread.is_at_bottom());
                });
                chat_manager.bus.on('unsubscribe_from_channel', self, self.on_channel_unsubscribed);
                chat_manager.bus.on('update_needaction', self, self.throttled_render_sidebar);
                chat_manager.bus.on('update_starred', self, self.throttled_render_sidebar);
                chat_manager.bus.on('update_channel_unread_counter', self, self.throttled_render_sidebar);
                chat_manager.bus.on('update_dm_presence', self, self.throttled_render_sidebar);
                self.thread.$el.on("scroll", null, _.debounce(function () {
                    if (self.thread.is_at_bottom()) {
                        chat_manager.mark_channel_as_seen(self.channel);
                    }
                }, 100));
            });
    },

    select_message: function(message_id) {
        this.$el.addClass('o_mail_selection_mode');
        var message = chat_manager.get_message(message_id);
        this.selected_message = message;
        var subject = "Re: " + message.record_name;
        this.extended_composer.set_subject(subject);
        if (this.channel.type !== 'static') {
            this.basic_composer.toggle(false);
        }
        this.extended_composer.toggle(true);
        this.thread.scroll_to({id: message_id, duration: 200, only_if_necessary: true});
        this.extended_composer.focus('body');
    },

    unselect_message: function() {
        this.basic_composer.toggle(this.channel.type !== 'static' && !this.channel.mass_mailing);
        this.extended_composer.toggle(this.channel.type !== 'static' && this.channel.mass_mailing);
        if (!config.device.touch) {
            var composer = this.channel.mass_mailing ? this.extended_composer : this.basic_composer;
            composer.focus();
        }
        this.$el.removeClass('o_mail_selection_mode');
        this.thread.unselect();
        this.selected_message = null;
    },

    render_sidebar: function () {
        var self = this;
        var $sidebar = this._render_sidebar({
            active_channel_id: this.channel ? this.channel.id: undefined,
            channels: chat_manager.get_channels(),
            needaction_counter: chat_manager.get_needaction_counter(),
            starred_counter: chat_manager.get_starred_counter(),
        });
        this.$(".o_mail_chat_sidebar").html($sidebar.contents());

        this.$('.o_mail_add_channel[data-type=public]').find("input").autocomplete({
            source: function(request, response) {
                self.last_search_val = _.escape(request.term);
                self.do_search_channel(self.last_search_val).done(function(result){
                    result.push({
                        'label':  _.str.sprintf('<strong>'+_t("Create %s")+'</strong>', '<em>"#'+self.last_search_val+'"</em>'),
                        'value': '_create',
                    });
                    response(result);
                });
            },
            select: function(event, ui) {
                if (self.last_search_val) {
                    if (ui.item.value === '_create') {
                        chat_manager.create_channel(self.last_search_val, "public");
                    } else {
                        chat_manager.join_channel(ui.item.id);
                    }
                }
            },
            focus: function(event) {
                event.preventDefault();
            },
            html: true,
        });

        this.$('.o_mail_add_channel[data-type=dm]').find("input").autocomplete({
            source: function(request, response) {
                self.last_search_val = _.escape(request.term);
                chat_manager.search_partner(self.last_search_val, 10).done(response);
            },
            select: function(event, ui) {
                var partner_id = ui.item.id;
                var dm = chat_manager.get_dm_from_partner_id(partner_id);
                if (dm) {
                    self.set_channel(dm);
                } else {
                    chat_manager.create_channel(partner_id, "dm");
                }
                // clear the input
                $(this).val('');
                return false;
            },
            focus: function(event) {
                event.preventDefault();
            },
        });

        this.$('.o_mail_add_channel[data-type=private]').find("input").on('keyup', this, function (event) {
            var name = _.escape($(event.target).val());
            if(event.which === $.ui.keyCode.ENTER && name) {
                chat_manager.create_channel(name, "private");
            }
        });
    },

    _render_sidebar: function (options) {
        return $(QWeb.render("mail.chat.Sidebar", options));
    },

    render_snackbar: function (template, context, timeout) {
        if (this.$snackbar) {
            this.$snackbar.remove();
        }
        timeout = timeout || 20000;
        this.$snackbar = $(QWeb.render(template, context));
        this.$('.o_mail_chat_content').append(this.$snackbar);
        // Hide snackbar after [timeout] milliseconds (by default, 20s)
        var $snackbar = this.$snackbar;
        setTimeout(function() { $snackbar.fadeOut(); }, timeout);
    },

    do_search_channel: function(search_val){
        var Channel = new Model("mail.channel");
        return Channel.call('channel_search_to_join', [search_val]).then(function(result){
            var values = [];
            _.each(result, function(channel){
                var escaped_name = _.escape(channel.name);
                values.push(_.extend(channel, {
                    'value': escaped_name,
                    'label': escaped_name,
                }));
            });
            return values;
        });
    },

    set_channel: function (channel) {
        var self = this;
        // Store scroll position of previous channel
        if (this.channel) {
            this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
        }
        var new_channel_scrolltop = this.channels_scrolltop[channel.id];

        this.channel = channel;
        this.messages_separator_position = undefined; // reset value on channel change
        this.unread_counter = this.channel.unread_counter;
        this.last_seen_message_id = this.channel.last_seen_message_id;
        if (this.$snackbar) {
            this.$snackbar.remove();
        }

        this.action.context.active_id = channel.id;
        this.action.context.active_ids = [channel.id];

        return this.fetch_and_render_thread().then(function () {
            // Mark channel's messages as read and clear needactions
            if (channel.type !== 'static') {
                chat_manager.mark_channel_as_seen(channel);
            }

            // Update control panel
            self.set("title", '#' + channel.name);
            // Hide 'unsubscribe' button in state channels and DM and channels with group-based subscription
            self.$buttons
                .find('.o_mail_chat_button_unsubscribe')
                .toggle(channel.type !== "dm" && channel.type !== 'static' && ! channel.group_based_subscription);
            // Hide 'invite', 'unsubscribe' and 'settings' buttons in static channels and DM
            self.$buttons
                .find('.o_mail_chat_button_invite, .o_mail_chat_button_settings')
                .toggle(channel.type !== "dm" && channel.type !== 'static');
            self.$buttons
                .find('.o_mail_chat_button_mark_read')
                .toggle(channel.id === "channel_inbox");
            self.$buttons
                .find('.o_mail_chat_button_unstar_all')
                .toggle(channel.id === "channel_starred");

            self.$('.o_mail_chat_channel_item')
                .removeClass('o_active')
                .filter('[data-channel-id=' + channel.id + ']')
                .removeClass('o_unread_message')
                .addClass('o_active');

            var $new_messages_separator = self.$('.o_thread_new_messages_separator');
            if ($new_messages_separator.length) {
                self.thread.$el.scrollTo($new_messages_separator);
            } else {
                self.thread.scroll_to({offset: new_channel_scrolltop});
            }

            // Update control panel before focusing the composer, otherwise focus is on the searchview
            self.update_cp();
            if (config.device.size_class === config.device.SIZES.XS) {
                self.$('.o_mail_chat_sidebar').hide();
            }

            // Display and focus the adequate composer, and unselect possibly selected message
            // to prevent sending messages as reply to that message
            self.unselect_message();

            self.action_manager.do_push_state({
                action: self.action.id,
                active_id: self.channel.id,
            });
        });
    },

    get_thread_rendering_options: function (messages) {
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

    fetch_and_render_thread: function () {
        var self = this;
        return chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function(result) {
            self.thread.render(result, self.get_thread_rendering_options(result));
            self.update_button_status(result.length === 0);
        });
    },

    update_button_status: function (disabled) {
        if (this.channel.id === "channel_inbox") {
            this.$buttons
                .find('.o_mail_chat_button_mark_read')
                .toggleClass('disabled', disabled);
        }
        if (this.channel.id === "channel_starred") {
            this.$buttons
                .find('.o_mail_chat_button_unstar_all')
                .toggleClass('disabled', disabled);
        }
    },

    load_more_messages: function () {
        var self = this;
        var oldest_msg_id = this.$('.o_thread_message').first().data('messageId');
        var oldest_msg_selector = '.o_thread_message[data-message-id="' + oldest_msg_id + '"]';
        var offset = -framework.getPosition(document.querySelector(oldest_msg_selector)).top;
        return chat_manager
            .get_messages({channel_id: this.channel.id, domain: this.domain, load_more: true})
            .then(function(result) {
                if (self.messages_separator_position === 'top') {
                    self.messages_separator_position = undefined; // reset value to re-compute separator position
                }
                self.thread.render(result, self.get_thread_rendering_options(result));
                offset += framework.getPosition(document.querySelector(oldest_msg_selector)).top;
                self.thread.scroll_to({offset: offset});
            });
    },

    update_cp: function () {
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

    do_show: function () {
        this._super.apply(this, arguments);
        this.update_cp();
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: this.channel.id,
        });
    },

    on_search: function (domains) {
        var result = pyeval.sync_eval_domains_and_contexts({
            domains: domains
        });

        this.domain = result.domain;
        this.fetch_and_render_thread();
    },

    on_post_message: function (message) {
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
            .then(function() {
                if (self.selected_message) {
                    self.render_snackbar('mail.chat.MessageSentSnackbar', {record_name: self.selected_message.record_name}, 5000);
                    self.unselect_message();
                } else {
                    self.thread.scroll_to();
                }
            })
            .fail(function () {
                // todo: display notification
            });
    },
    on_new_message: function (message) {
        var self = this;
        if (_.contains(message.channel_ids, this.channel.id)) {
            if (this.channel.type !== 'static' && this.thread.is_at_bottom()) {
                chat_manager.mark_channel_as_seen(this.channel);
            }

            var should_scroll = this.thread.is_at_bottom();
            this.fetch_and_render_thread().then(function () {
                if (should_scroll) {
                    self.thread.scroll_to({id: message.id});
                }
            });
        }
        // Re-render sidebar to indicate that there is a new message in the corresponding channels
        this.render_sidebar();
        // Dump scroll position of channels in which the new message arrived
        this.channels_scrolltop = _.omit(this.channels_scrolltop, message.channel_ids);
    },
    on_update_message: function (message) {
        var self = this;
        var current_channel_id = this.channel.id;
        if ((current_channel_id === "channel_starred" && !message.is_starred) ||
            (current_channel_id === "channel_inbox" && !message.is_needaction)) {
            chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function (messages) {
                var options = self.get_thread_rendering_options(messages);
                self.thread.remove_message_and_render(message.id, messages, options).then(function () {
                    self.update_button_status(messages.length === 0);
                });
            });
        } else if (_.contains(message.channel_ids, current_channel_id)) {
            this.fetch_and_render_thread();
        }
    },
    on_new_channel: function (channel) {
        this.render_sidebar();
        if (channel.autoswitch) {
            this.set_channel(channel);
        }
    },
    on_channel_unsubscribed: function (channel_id) {
        if (this.channel.id === channel_id) {
            this.set_channel(chat_manager.get_channel("channel_inbox"));
        }
        this.render_sidebar();
        delete this.channels_scrolltop[channel_id];
    },
    on_composer_input_focused: function () {
        var composer = this.channel.mass_mailing ? this.extended_composer : this.basic_composer;
        var commands = chat_manager.get_commands(this.channel);
        var partners = chat_manager.get_mention_partner_suggestions(this.channel);
        composer.mention_set_enabled_commands(commands);
        composer.mention_set_prefetched_partners(partners);
    },

    on_click_button_invite: function () {
        var title = _.str.sprintf(_t('Invite people to #%s'), this.channel.name);
        new PartnerInviteDialog(this, title, this.channel.id).open();
    },

    on_click_button_unsubscribe: function () {
        chat_manager.unsubscribe(this.channel);
    },
    on_click_button_settings: function() {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            res_id: this.channel.id,
            views: [[false, 'form']],
            target: 'current'
        });
    },
    destroy: function() {
        this.$buttons.off().destroy();
        this._super.apply(this, arguments);
    },
});


core.action_registry.add('mail.chat.instant_messaging', ChatAction);

});
