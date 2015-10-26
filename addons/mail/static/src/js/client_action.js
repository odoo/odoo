odoo.define('mail.chat_client_action', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatComposer = require('mail.ChatComposer');
var ChatThread = require('mail.ChatThread');

var config = require('web.config');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Model = require('web.Model');

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
        this.PartnersModel = new Model('res.partner');
    },
    start: function(){
        var self = this;
        this.$input = this.$('.o_mail_chat_partner_invite_input');
        this.$input.select2({
            width: '100%',
            allowClear: true,
            multiple: true,
            formatResult: function(item){
                var css_class = "fa-circle" + (item.im_status === 'online' ? "" : "-o");
                return $('<span class="fa">').addClass(css_class).text(item.text);
            },
            query: function (query) {
                self.PartnersModel.call('im_search', [query.term, 20]).then(function(result){
                    var data = [];
                    _.each(result, function(partner){
                        partner.text = partner.name;
                        data.push(partner);
                    });
                    query.callback({results: data});
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
            return ChannelModel.call('channel_invite', [], {ids : [this.channel_id], partner_ids: _.pluck(data, 'id')})
                .then(function(){
                    var names = _.pluck(data, 'text').join(', ');
                    var notification = _.str.sprintf(_t('You added <b>%s</b> to the conversation.'), names);
                    self.do_notify(_t('New people'), notification);
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
            this.unsubscribe_from_channel(chat_manager.get_channel(channel_id));
        },
    },

    on_attach_callback: function () {
        this.thread.scroll_to({offset: this.channels_scrolltop[this.channel.id]});
    },
    on_detach_callback: function () {
        this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
    },

    init: function(parent, action, options) {
        this._super.apply(this, arguments);
        this.action_manager = parent;
        this.domain = [];
        this.action = action;
        this.options = options || {};
        this.channels_scrolltop = {};
    },

    start: function() {
        var self = this;

        // create searchview
        var options = {
            $buttons: $("<div>"),
            action: this.action,
            disable_groupby: true,
        };
        var dataset = new data.DataSetSearch(this, 'mail.message');
        var view_id = (this.action && this.action.search_view_id && this.action.search_view_id[0]) || false;
        var default_channel_id = this.options.active_id ||
                                 this.action.context.active_id ||
                                 this.action.params.default_active_id ||
                                 'channel_inbox';
        this.searchview = new SearchView(this, dataset, view_id, {}, options);
        this.searchview.on('search_data', this, this.on_search);

        this.composer = new ChatComposer(this, {
            get_channel_info: function () {
                return { channel_id: self.channel.id };
            },
        });
        this.thread = new ChatThread(this, {
            no_content_helper: this.action.help,
        });

        this.$buttons = $(QWeb.render("mail.chat.ControlButtons", {}));
        this.$buttons.find('button').css({display:"inline-block"});
        this.$buttons.on('click', '.o_mail_chat_button_invite', this.on_click_button_invite);
        this.$buttons.on('click', '.o_mail_chat_button_detach', this.on_click_button_detach);
        this.$buttons.on('click', '.o_mail_chat_button_unsubscribe', this.on_click_button_unsubscribe);
        this.$buttons.on('click', '.o_mail_chat_button_settings', this.on_click_button_settings);
        this.$buttons.on('click', '.o_mail_toggle_channels', function () {
            self.$('.o_mail_chat_sidebar').slideToggle(200);
        });

        this.thread.on('redirect', this, this.on_redirect);
        this.thread.on('redirect_to_channel', this, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel.id === channel_id) {
                this.set_channel(channel);
            } else {
                chat_manager.join_channel(channel_id);
            }
        });
        this.thread.on('load_more_messages', this, this.load_more_messages);
        this.thread.on('mark_as_read', this, function (message_id) {
            chat_manager.mark_as_read(message_id);
        });
        this.thread.on('toggle_star_status', this, function (message_id) {
            chat_manager.toggle_star_status(message_id);
        });
        this.composer.on('post_message', this, this.on_post_message);

        var def1 = this.thread.prependTo(this.$('.o_mail_chat_content'));
        var def2 = this.composer.appendTo(this.$('.o_mail_chat_content'));
        var def3 = this.searchview.appendTo($("<div>"));

        this.render_sidebar();

        return $.when(def1, def2, def3)
            .then(this.set_channel.bind(this, chat_manager.get_channel(default_channel_id)))
            .then(function () {
                chat_manager.bus.on('new_message', self, self.on_new_message);
                chat_manager.bus.on('update_message', self, self.on_update_message);
                chat_manager.bus.on('new_channel', self, self.on_new_channel);
                chat_manager.bus.on('anyone_listening', self, function (channel, query) {
                    query.is_displayed = query.is_displayed || channel.id === self.channel.id;
                });
                chat_manager.bus.on('update_needaction', self, self.on_update_needaction);
            });
    },

    render_sidebar: function () {
        var self = this;
        var $sidebar = QWeb.render("mail.chat.Sidebar", {
            channels: chat_manager.get_channels(),
            needaction_counter: chat_manager.get_needaction_counter()
        });
        this.$(".o_mail_chat_sidebar").replaceWith($sidebar);

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
                self.do_search_partner(self.last_search_val).done(function(result){
                    response(result);
                });
            },
            select: function(event, ui) {
                var partner_id = ui.item.id;
                chat_manager.create_channel(partner_id, "dm");
            },
            focus: function(event) {
                event.preventDefault();
            },
            html: true,
        });

        this.$('.o_mail_add_channel[data-type=private]').find("input").on('keyup', this, function (event) {
            var name = _.escape($(event.target).val());
            if(event.which === $.ui.keyCode.ENTER && name) {
                chat_manager.create_channel(name, "private");
            }
        });
    },

    do_search_channel: function(search_val){
        var Channel = new Model("mail.channel");
        return Channel.call('channel_search_to_join', [search_val]).then(function(result){
            var values = [];
            _.each(result, function(channel){
                values.push(_.extend(channel, {
                    'value': channel.name,
                    'label': channel.name,
                }));
            });
            return values;
        });
    },

    do_search_partner: function (search_val) {
        var Partner = new Model("res.partner");
        return Partner.call('im_search', [search_val, 20]).then(function(result){
            var values = [];
            _.each(result, function(user){
                values.push(_.extend(user, {
                    'value': user.name,
                    'label': user.name,
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

        // Update control panel
        this.set("title", channel.name);
        // Hide 'detach' button in static channels
        this.$buttons
            .find('.o_mail_chat_button_detach')
            .toggle(channel.type !== "static");
        // Hide 'invite', 'unsubscribe' and 'settings' buttons in static channels and DM
        this.$buttons
            .find('.o_mail_chat_button_invite, .o_mail_chat_button_unsubscribe, .o_mail_chat_button_settings')
            .toggle(channel.type !== "static" && channel.type !== "dm");
        this.update_cp();

        this.action.context.active_id = channel.id;
        this.action.context.active_ids = [channel.id];

        this.$('.o_mail_chat_channel_item')
            .removeClass('o_active')
            .filter('[data-channel-id=' + channel.id + ']')
            .removeClass('o_unread_message')
            .addClass('o_active');

        this.$('.o_chat_composer').toggle(channel.type !== 'static');

        return this.fetch_and_render_thread().then(function () {
            self.thread.scroll_to({offset: new_channel_scrolltop});
            if (!config.device.touch) {
                self.composer.focus();
            }
            if (config.device.size_class === config.device.SIZES.XS) {
                self.$('.o_mail_chat_sidebar').hide();
            }

            self.action_manager.do_push_state({
                action: self.action.id,
                active_id: self.channel.id,
            });
        });
    },
    unsubscribe_from_channel: function (channel) {
        var self = this;
        chat_manager
            .unsubscribe(channel)
            .then(this.render_sidebar.bind(this))
            .then(this.set_channel.bind(this, chat_manager.get_channel("channel_inbox")))
            .then(function () {
                if (_.contains(['public', 'private'], channel.type)) {
                    var msg = _.str.sprintf(_t('You unsubscribed from <b>%s</b>.'), channel.name);
                    self.do_notify(_t("Unsubscribed"), msg);
                }
                delete self.channels_scrolltop[channel.id];
            });
    },

    get_thread_rendering_options: function () {
        return {
            display_load_more: !chat_manager.all_history_loaded(this.channel, this.domain),
            display_needactions: this.channel.display_needactions,
            channel_id: this.channel.id,
        };
    },

    fetch_and_render_thread: function () {
        var self = this;
        return chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function(result) {
            self.thread.render(result, self.get_thread_rendering_options());
        });
    },

    load_more_messages: function () {
        var self = this;
        var oldest_msg_id = this.$('.o_thread_message').first().data('messageId');
        var oldest_msg_selector = '.o_thread_message[data-message-id="' + oldest_msg_id + '"]';
        var offset = -framework.getPosition(document.querySelector(oldest_msg_selector)).top;
        return chat_manager
            .fetch_more(this.channel, this.domain)
            .then(function(result) {
                self.thread.render(result, self.get_thread_rendering_options());
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
                $searchview_buttons: this.searchview.$buttons.contents(),
            },
            searchview: this.searchview,
        });
    },

    on_search: function (domains) {
        var result = pyeval.sync_eval_domains_and_contexts({
            domains: domains
        });

        this.domain = result.domain;
        this.fetch_and_render_thread();
    },

    /**
     * Callback performed on o_mail_redirect element clicked
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view.
     */
    on_redirect: function (res_model, res_id) {
        var self = this;
        var redirect_to_document = function (res_model, res_id) {
            self.action_manager.do_push_state({
                model: res_model,
                id: res_id,
            });
            self.do_action({
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: res_model,
                views: [[false, 'form']],
                res_id: res_id,
            }, {
                on_reverse_breadcrumb: self.on_reverse_breadcrumb,
            });
        };

        if (res_model === "res.partner") {
            var domain = [["partner_id", "=", res_id]];
            new Model('res.users').call("search", [domain]).then(function (user_ids) {
                if (user_ids.length && user_ids[0] !== session.uid) {
                    chat_manager.create_channel(res_id, 'dm').then(function (channel) {
                        if (!self.channel || self.channel.id !== channel.id) {
                            self.set_channel(channel);
                        }
                    });
                } else {
                    redirect_to_document(res_model, res_id);
                }
            });
        } else {
            redirect_to_document(res_model, res_id);
        }
    },
    on_reverse_breadcrumb: function () {
        this.update_cp(); // do not reload the client action, just display it, but a refresh of the control panel is needed.
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: this.channel.id,
        });
    },
    on_post_message: function (message) {
        message.channel_id = this.channel.id;
        chat_manager
            .post_message(message)
            .fail(function () {
                // todo: display notification
            });
    },
    on_new_message: function (message) {
        var self = this;
        if (_.contains(message.channel_ids, this.channel.id)) {
            this.fetch_and_render_thread().then(function () {
                self.thread.scroll_to({id: message.id});
            });
        }
        // Indicate in the sidebar that there is a new message in the corresponding channels
        _.each(_.without(message.channel_ids, this.channel.id), function (channel_id) {
                self.$('.o_mail_chat_channel_item')
                    .filter('[data-channel-id=' + channel_id + ']')
                    .addClass('o_unread_message');
        });
        // Dump scroll position of channels in which the new message arrived
        this.channels_scrolltop = _.omit(this.channels_scrolltop, message.channel_ids);
    },
    on_update_message: function (message) {
        var self = this;
        var current_channel_id = this.channel.id;
        if ((current_channel_id === "channel_starred" && !message.is_starred) ||
            (current_channel_id === "channel_inbox" && !message.is_needaction)) {
            chat_manager.fetch(this.channel, this.domain).then(function (messages) {
                var options = self.get_thread_rendering_options();
                self.thread.remove_message_and_render(message.id, messages, options);
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
    on_update_needaction: function () {
        var $needaction_badge = QWeb.render("mail.chat.SidebarNeedaction", {
            needaction_counter: chat_manager.get_needaction_counter()
        });
        this.$('.o_mail_sidebar_needaction').replaceWith($needaction_badge);
    },

    on_click_button_invite: function () {
        var title = _.str.sprintf(_t('Invite people to %s'), this.channel.name);
        new PartnerInviteDialog(this, title, this.channel.id).open();
    },
    on_click_button_detach: function () {
        chat_manager.detach_channel(this.channel);
    },

    on_click_button_unsubscribe: function () {
        this.unsubscribe_from_channel(this.channel);
    },
    on_click_button_settings: function() {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            res_id: this.channel.id,
            views: [[false, 'form']],
            target: 'current'
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
});


core.action_registry.add('mail.chat.instant_messaging', ChatAction);

});
