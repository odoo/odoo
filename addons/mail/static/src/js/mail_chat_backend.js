odoo.define('mail.chat_backend', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');
var ControlPanelMixin = require('web.ControlPanelMixin');
var SearchView = require('web.SearchView');
var WebClient = require('web.WebClient');

var session = require('web.session');
var web_client = require('web.web_client');

var mail_chat_common = require('mail.chat_common');
var mail_thread = require('mail.thread');

var _t = core._t;
var QWeb = core.qweb;
var internal_bus = core.bus;


/**
 * Widget handeling the channels, in the backend
 *
 * Responsible to listen the bus and apply action with the received message.  Add layer to coordinate the
 * folded conversation and trigger event for the InstantMessagingView client action (using internal
 * comminication bus). It is a component of the WebClient.
 **/
var ConversationManagerBackend = mail_chat_common.ConversationManager.extend({
    _setup: function(init_data){
        var self = this;
        this._super.apply(this, arguments);
        _.each(init_data.notifications, function(n){
            self.on_notification(n);
        });
    },
    // window title
    window_title_change: function() {
        this._super.apply(this, arguments);
        var title;
        if (this.get("waiting_messages") !== 0) {
            title = _.str.sprintf(_t("%d Messages"), this.get("waiting_messages"));
        }
        web_client.set_title_part("im_messages", title);
    },
    // sessions and messages
    session_apply: function(active_session){
        // for chat windows
        if(active_session.is_minimized || (!active_session.is_minimized && active_session.state === 'closed')){
            this._super.apply(this, arguments);
        }
        // for client action
        if(!active_session.is_minimized){ // if not minimized,
            internal_bus.trigger('mail_session_receive', active_session);
        }
    },
    message_receive: function(message) {
        var actual_channel_ids = _.map(_.keys(this.sessions), function(item){
            return parseInt(item);
        });
        var message_channel_ids = message.channel_ids;
        if(_.intersection(actual_channel_ids, message_channel_ids).length){
           this._super.apply(this, arguments);
        }
        // broadcast the message to the NotificationButton and the InstantMessagingView
        internal_bus.trigger('mail_message_receive', message);
        // increment the needaction top counter
        if(message.needaction_partner_ids && _.contains(message.needaction_partner_ids, session.partner_id)){
            internal_bus.trigger('mail_needaction_new', 1);
        }
    },
});


/**
 * Widget Minimized Conversation
 *
 * Add layer of WebClient integration, and user fold state handling (comminication with server)
 **/
mail_chat_common.Conversation.include({
    session_fold: function(state){
        var self = this;
        var args = arguments;
        var super_call = this._super;
        // broadcast the state changing
        return new Model("mail.channel").call("channel_fold", [], {"uuid" : this.get("session").uuid, "state" : state}).then(function(){
            super_call.apply(self, args);
        });
    },
});

/**
 * Widget : Patch for WebClient
 *
 * Create the conversation manager, and attach it to the web_client.
 **/
WebClient.include({
    show_application: function(){
        var self = this;
        var args = arguments;
        var super_call = this._super;
        this.mail_conversation_manager = new ConversationManagerBackend(this);
        this.mail_conversation_manager.start().then(function(){
            super_call.apply(self, args);
            self.mail_conversation_manager.bus.start_polling();
        });
    },
});


/**
 * Widget Top Menu Notification Counter
 *
 * Counter of notification in the Systray Menu. Need to know if InstantMessagingView is displayed to
 * increment (or not) the counter. On click, should redirect to the client action.
 **/
var NotificationTopButton = Widget.extend({
    template:'mail.chat.NotificationTopButton',
    events: {
        "click": "on_click",
    },
    init: function(){
        this._super.apply(this, arguments);
        this.set('counter', 0);
    },
    willStart: function(){
        var self = this;
        return $.when(session.rpc('/mail/needaction'), this._super()).then(function(needaction_count){
            self.set('counter', needaction_count);
        });
    },
    start: function() {
        this.on("change:counter", this, this.on_change_counter);
        // events
        internal_bus.on('mail_needaction_new', this, this.counter_increment);
        internal_bus.on('mail_needaction_done', this, this.counter_decrement);
        return this._super();
    },
    counter_increment: function(inc){
        this.set('counter', this.get('counter')+inc);
    },
    counter_decrement: function(dec){
        this.set('counter', this.get('counter')-dec);
    },
    on_change_counter: function() {
        this.$('.fa-comment').html(this.get('counter') || '');
    },
    on_click: function(e){
        e.preventDefault();
        this.do_action({
            type: 'ir.actions.client',
            tag: 'mail.chat.instant_messaging',
            params: {
                'default_active_id': 'channel_inbox',
            },
        }, {
            clear_breadcrumbs: true,
        });
    },
});

SystrayMenu.Items.push(NotificationTopButton);


/**
 * Abstract Class to 'Add More/Search' Widget
 *
 * Inputbox using jQueryUI autocomplete to fetch selection, like a Many2One field (on form view)
 * Used to create or pin a mail.channel or a res.partner on the InstantMessagingView
 **/
var AbstractAddMoreSearch = Widget.extend({
    template: 'mail.chat.AbstractAddMoreSearch',
    events: {
        "click .o_mail_chat_add_more_text": "on_click_text",
        "blur .o_mail_chat_search_input": "_toggle_elements",
    },
    init: function(parent, options){
        this._super.apply(this, arguments);
        options = _.defaults(options || {}, {
            'can_create': false,
            'label': _t('+ Add More'),
        });
        this.limit = 10;
        this.can_create = options.can_create;
        this.label = options.label;
    },
    start: function(){
        this.last_search_val = false;
        this.$input = this.$('.o_mail_chat_search_input');
        this._bind_events();
        return this._super();
    },
    _bind_events: function(){
        // autocomplete
        var self = this;
        this.$input.autocomplete({
            source: function(request, response) {
                self.last_search_val = request.term;
                self.do_search(request.term).done(function(result){
                    if(self.can_create){
                        result.push({
                            'label':  _.str.sprintf('<strong>'+_t("Create %s")+'</strong>', '<em>"'+self.last_search_val+'"</em>'),
                            'value': '_create',
                        });
                    }
                    response(result);
                });
            },
            select: function(event, ui) {
                self.on_click_item(ui.item);
            },
            focus: function(event) {
                event.preventDefault();
            },
            html: true,
        });
    },
    // ui
    _toggle_elements: function(){
        this.$('.o_mail_chat_add_more_text').toggle();
        this.$('.o_mail_chat_add_more_search_bar').toggle();
        this.$input.val('');
        this.$input.focus();
    },
    on_click_text: function(event){
        event.preventDefault();
        this._toggle_elements();
    },
    // to be redefined
    do_search: function(){
        return $.when();
    },
    on_click_item: function(item){
        if(item.value === '_create'){
            if(this.last_search_val){
                this.trigger('item_create', this.last_search_val);
            }
        }else{
            this.trigger('item_clicked', item);
        }
    },
});

var PartnerAddMoreSearch = AbstractAddMoreSearch.extend({
    /**
     * Do the search call
     * @override
     */
    do_search: function(search_val){
        var Partner = new Model("res.partner");
        return Partner.call('im_search', [search_val, this.limit]).then(function(result){
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
});

var ChannelAddMoreSearch = AbstractAddMoreSearch.extend({
    /**
     * Do the search call
     * @override
     */
    do_search: function(search_val){
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
});

var PrivateGroupAddMoreSearch = AbstractAddMoreSearch.extend({
    _bind_events: function(){
       // don't call the super to avoid autocomplete
       this.$input.on('keyup', this, this.on_keydown);
    },
    on_keydown: function(event){
        if(event.which === $.ui.keyCode.ENTER && this.$input.val()){
            this.trigger('item_create', this.$input.val());
        }
    },
});


/**
 * Widget : Invite People to Channel Dialog
 *
 * Popup containing a 'many2many_tags' custom input to select multiple partners.
 * Search user according to the input, and trigger event when selection is validated.
 **/
var PartnerInviteDialog = Dialog.extend({
    dialog_title: _t('Invite people'),
    template: "mail.chat.PartnerInviteDialog",
    init: function(parent, options){
        options = _.defaults(options || {}, {
            buttons: [{
                text: _t("Invite"),
                close: true,
                classes: "btn-primary",
                click: _.bind(this.on_click_add, this),
            }],
            channel: undefined,
        });
        this._super.apply(this, arguments);
        this.set("partners", []);
        this.channel = options.channel;
        this.PartnersModel = new Model('res.partner');
        this.ChannelModel = new Model('mail.channel');
        this.limit = 20;
    },
    start: function(){
        var self = this;
        this.$('.o_mail_chat_partner_invite_input').select2({
            width: '100%',
            allowClear: true,
            multiple: true,
            formatResult: function(item){
                if(item.im_status === 'online'){
                    return '<span class="fa fa-circle"> ' + item.text + '</span>';
                }
                return '<span class="fa fa-circle-o"> ' + item.text + '</span>';
            },
            query: function (query) {
                self.PartnersModel.call('im_search', [query.term, self.limit]).then(function(result){
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
        var data = this.$('.o_mail_chat_partner_invite_input').select2('data');
        if(data.length >= 1){
            this.ChannelModel.call('channel_invite', [], {"ids" : [this.channel.id], 'partner_ids': _.pluck(data, 'id')}).then(function(){
                var names = _.pluck(data, 'text').join(', ');
                self.do_notify(_t('New people'), _.str.sprintf(_t('You added <b>%s</b> to the conversation.'), names));
                self.close();
            });
        }else{
            self.close();
        }
    },
});

/**
 * Client Action : Instant Messaging View, inspired by Slack.com
 *
 * Action replacing the Inbox, and the list of group (mailing list, multiple conversation, rooms, ...)
 * Includes real time messages (received and sent), creating group, channel, chat conversation, ...
 **/
var ChatMailThread = Widget.extend(mail_thread.MailThreadMixin, ControlPanelMixin, {
    template: 'mail.chat.ChatMailThread',
    events: {
        // events from MailThreadMixin
        "click .o_mail_redirect": "on_click_redirect",
        "click .o_mail_thread_message_star": "on_message_star",
        // events specific for ChatMailThread
        "click .o_mail_chat_channel_item": "on_click_channel",
        "click .o_mail_chat_partner_item": "on_click_partner",
        "click .o_mail_chat_partner_unpin": "on_click_partner_unpin",
        "click .o_mail_thread_message_needaction": "on_message_needaction",
    },
    init: function (parent, action) {
        this._super.apply(this, arguments);
        // attributes
        this.action_manager = parent;
        this.help_message = action.help || '';
        this.context = action.context;
        this.action = action;
        this.loading_history = false;
        this.chatter_needaction_auto = false;
        this.options = this.action.params;
        // mail thread mixin
        mail_thread.MailThreadMixin.init.call(this);
        // components : conversation manager and search widget (channel_type + '_search_widget')
        this.conv_manager = web_client.mail_conversation_manager;
        this.channel_search_widget = new ChannelAddMoreSearch(this, {'label': _t('+ Subscribe'), 'can_create': true});
        this.group_search_widget = new PrivateGroupAddMoreSearch(this, {'label': _t('+ New private group'), 'can_create': true});
        this.partner_search_widget = new PartnerAddMoreSearch(this);
        // options (update the default of MailThreadMixin)
        this.options = _.extend(this.options, {
            'display_document_link': true,
            'display_needaction_button': true,
            'emoji_list': this.conv_manager.emoji_list,
            'default_username': _t('Anonymous'),
        });
        this.emoji_set_substitution(this.conv_manager.emoji_list);
        // channel business
        this.channels = {};
        this.mapping = {}; // mapping partner_id/channel_id for 'direct message' channel
        this.set('current_channel_id', false);
        this.set('needaction_inbox_counter', 0);
        this.search_domain = [];
        // channel slots
        this.set('channel_channel', []);
        this.set('channel_direct_message', []);
        this.set('channel_private_group', []);
        this.set('partners', []);
        // models
        this.ChannelModel = new Model('mail.channel', this.context);
        // control panel items
        this.control_elements = {};
    },
    willStart: function(){
        var self = this;
        return session.rpc('/mail/client_action').then(function(result){
            self.chatter_needaction_auto = result.chatter_needaction_auto;
            self.set('needaction_inbox_counter', result.needaction_inbox_counter);
            self.set('partners', result.channel_slots.partners);
            self.mapping = result.channel_slots.mapping;
            self._channel_slot(_.omit(result.channel_slots, 'partners', 'mapping'));
        });
    },
    start: function(){
        var self = this;
        this._super.apply(this, arguments);
        mail_thread.MailThreadMixin.start.call(this);
        // channel business events
        this.on("change:current_channel_id", this, this.channel_change);
        this.on("change:channel_channel", this, function(){
            self.channel_render('channel_channel');
        });
        this.on("change:channel_private_group", this, function(){
            self.channel_render('channel_private_group');
        });
        this.on("change:partners", this, this.partner_render);

        // search widget for channel
        this.channel_search_widget.insertAfter(this.$('.o_mail_chat_channel_slot_channel_channel'));
        this.channel_search_widget.on('item_create', this, function(name){
            self.channel_create(name, 'public');
        });
        this.channel_search_widget.on('item_clicked', this, function(item){
            self.channel_join_and_get_info(item.id).then(function(channel){
                self.channel_apply(channel);
            });
        });
        // search widget for direct message
        this.partner_search_widget.insertAfter(this.$('.o_mail_chat_channel_slot_partners'));
        this.partner_search_widget.on('item_clicked', this, function(item){
            self.channel_get([item.id]);
            self.partner_add(item);
        });
        // search widget for private group
        this.group_search_widget.insertAfter(this.$('.o_mail_chat_channel_slot_channel_private_group'));
        this.group_search_widget.on('item_create', this, function(name){
            self.channel_create(name, 'private');
        });

        // bind event to load history when scrolling near top
        this.$('.o_mail_chat_messages').scroll(function() {
            if ($(this).scrollTop() <= 50 && self.loading_history) { // at 50px of the top, load history
                self.message_load_history().then(function(messages){
                    if(messages.length < mail_thread.LIMIT_MESSAGE){
                        self.loading_history = false;
                    }
                });
            }
        });

        // needaction inbox counter
        this.on('change:needaction_inbox_counter', this, this.needaction_inbox_change);

        return $.when(this._super.apply(this, arguments), this.cp_render_searchview()).then(function(){
            // update control panel
            self.cp_render_buttons();
            // apply default channel
            var channel_id = self.context.active_id || self.action.params.default_active_id || 'channel_inbox';
            if(!_.isString(channel_id)){
                if(_.contains(_.keys(self.channels), channel_id)){
                    self.set('current_channel_id', channel_id);
                }else{
                    self.channel_info(channel_id).then(function(channel){
                        self.channel_apply(channel);
                    });
                }
            }else{
                self.set('current_channel_id', channel_id);
            }
            // internal communication (bind here to avoid receving message from bus when client action still not totally ready)
            internal_bus.on('mail_message_receive', self, self.message_receive);
            internal_bus.on('mail_session_receive', self, self.channel_receive);
            // needaction : the inbox has the same counter as the needaction top counter
            internal_bus.on('mail_needaction_new', this, function(inc){
                self.set('needaction_inbox_counter' , self.get('needaction_inbox_counter') + inc);
            });
            internal_bus.on('mail_needaction_done', this, function(dec){
                self.set('needaction_inbox_counter' , self.get('needaction_inbox_counter') - dec);
            });
        });
    },
    // event actions
    on_click_channel: function(event){
        event.preventDefault();
        var channel_id = this.$(event.currentTarget).data('channel-id');
        this.set('current_channel_id', channel_id);
    },
    on_click_partner: function(event){
        if(!this.$(event.target).hasClass('o_mail_chat_channel_unpin')){
            event.preventDefault();
            var partner_id = this.$(event.currentTarget).data('partner-id');
            if(this.mapping[partner_id]){ // don't fetch if channel already in local
                this.set('current_channel_id', this.mapping[partner_id]);
            }else{
                this.channel_get([partner_id]);
            }
        }
    },
    on_click_partner_unpin: function(event){
        event.preventDefault();
        var self = this;
        var $source = this.$(event.currentTarget);
        var partner_id = $source.data('partner-id');
        var channel_id = this.mapping[partner_id];
        var channel = this.channels[channel_id];
        this.channel_pin(channel.uuid, false).then(function(){
            self.set('partners', _.filter(self.get('partners'), function(p){ return p.id !== partner_id; }));
            self.channel_remove(channel_id);
            delete self.mapping[partner_id];
            // if unpin current channel, switch to inbox
            if(self.get('current_channel_id') === channel_id){
                self.set('current_channel_id', 'channel_inbox');
            }
        });
    },
    on_click_button_minimize: function(event){
        event.preventDefault();
        var current_channel = this.channels[this.get('current_channel_id')];
        if(current_channel){
            var channel_uuid = current_channel.uuid;
            return this.ChannelModel.call("channel_minimize", [channel_uuid, true]);
        }
        return $.Deferred().reject();
    },
    on_click_button_invite: function(){
        new PartnerInviteDialog(this, {
            title: _.str.sprintf(_t('Invite people to %s.'), this.get_current_channel_name()),
            channel: this.channels[this.get('current_channel_id')],
        }).open();
    },
    on_click_button_unsubscribe: function(){
        var self = this;
        this.ChannelModel.call('action_unfollow', [[this.get('current_channel_id')]]).then(function(){
            var channel = self.channels[self.get('current_channel_id')];
            var slot = self.get_channel_slot(channel);
            self.set(slot, _.filter(self.get(slot), function(c){ return c.id !== channel.id; }));
            self.do_notify(_t('Unsubscribe'), _.str.sprintf(_t('You unsubscribe from <b>%s</b>.'), self.get_current_channel_name()));
            self.set('current_channel_id', 'channel_inbox'); // jump to inbox
        });
    },
    on_click_button_settings: function(){
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "mail.channel",
            res_id: this.get('current_channel_id'),
            views: [[false, 'form']],
            target: 'current'
        }, {
            clear_breadcrumbs: true
        });
    },
    on_message_needaction: function(event){
        var self = this;
        mail_thread.MailThreadMixin.on_message_needaction.call(this, event).then(function(message_id){
            // decrement the needaction top counter
            internal_bus.trigger('mail_needaction_done', 1);
            // decrement the channel labels
            var treated_messages = _.filter(self.get('messages'), function(m){ return m.id == message_id; });
            if(treated_messages.length){
                self.needaction_decrement(treated_messages[0].channel_ids || []);
            }
        });
    },
    // control panel
    cp_update: function(){
        var self = this;
        var current_channel_id = this.get('current_channel_id');
        var current_channel_name = this.get_current_channel_name();
        // toggle cp buttons
        if(_.isString(current_channel_id)){
            self.control_elements.$buttons.find('button').hide();
        }else{
            self.control_elements.$buttons.find('button').show();
            var current_channel = this.channels[current_channel_id];
            if(current_channel.channel_type == 'chat'){
                self.control_elements.$buttons.find('.o_mail_chat_button_invite, .o_mail_chat_button_more').hide();
            }
        }
        // update control panel
        var status = {
            breadcrumbs: this.action_manager.get_breadcrumbs().concat([{'title': current_channel_name, 'action': _.clone(this)}]),
            cp_content: {
                $buttons: self.control_elements.$buttons,
                $searchview: self.control_elements.$searchview,
                $searchview_buttons: self.control_elements.$searchview_buttons,
                $switch_buttons: false,
                $pager: false,
            },
            searchview: self.searchview,
        };
        this.update_control_panel(status, {clear: false});
    },
    cp_render_buttons: function() {
        this.control_elements.$buttons = $(QWeb.render("mail.chat.ControlButtons", {}));
        this.control_elements.$buttons.on('click', '.o_mail_chat_button_minimize', _.bind(this.on_click_button_minimize, this));
        this.control_elements.$buttons.on('click', '.o_mail_chat_button_invite', _.bind(this.on_click_button_invite, this));
        this.control_elements.$buttons.on('click', '.o_mail_chat_button_unsubscribe', _.bind(this.on_click_button_unsubscribe, this));
        this.control_elements.$buttons.on('click', '.o_mail_chat_button_settings', _.bind(this.on_click_button_settings, this));
    },
    cp_render_searchview: function(){
        var self = this;
        var options = {
            $buttons: $("<div>"),
            action: this.action,
        };
        var view_id = (this.action && this.action.search_view_id && this.action.search_view_id[0]) || false;
        this.searchview = new SearchView(this, this.MessageDatasetSearch, view_id, {}, options);

        this.searchview.on('search_data', this, this.on_search);
        return $.when(this.searchview.appendTo($("<div>"))).done(function() {
            self.control_elements.$searchview = self.searchview.$el;
            self.control_elements.$searchview_buttons = self.searchview.$buttons.contents();
            // hack to hide 'group by' button, since it is not relevant
            self.searchview.$buttons.find('.oe-groupby-menu').hide();
        });
    },
    /**
     * Method call when action if done after redirecting (using 'on_click_redirect')
     * @override
     */
    on_reverse_breadcrumb: function(){
        var current_channel_id = this.get('current_channel_id');
        this.cp_update(); // do not reload the client action, just display it, but a refresh of the control panel is needed.
        // push state
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: current_channel_id,
        });
    },
    // messages search methods
    on_search: function(domains, contexts, groupbys){
        var self = this;
        return pyeval.eval_domains_and_contexts({
            domains: [[]].concat(domains || []),
            contexts: [this.context].concat(contexts || []),
            group_by_seq: groupbys || []
        }).done(function(results){
            if (results.error) {
                throw new Error(_.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s", JSON.stringify(results.error)));
            }
            // modify the search domain and do search
            self.search_domain = results.domain;
            return self.message_load_new();
        });
    },
    // channels
    /**
     * Set the channel slot
     * @param {Object[]} fetch_result : should contains only the slot name (as key) and the list of channel header as value.
     */
    _channel_slot: function(fetch_result){
        var self = this;
        var channel_slots = _.keys(fetch_result);
        _.each(channel_slots, function(slot){
            // update the channel slot
            self.set(slot, fetch_result[slot]);
            // flatten the result : update the complete channel list
            _.each(fetch_result[slot], function(channel){
                self.channels[channel.id] = channel;
            });
        });
    },
    /**
     * Apply a channel means adding it, and swith to it
     * @param {Object} channel : channel header
     */
    channel_apply: function(channel){
        this.channel_add(channel);
        this.set('current_channel_id', channel.id);
    },
    /**
     * Add the given channel, or update it if already exists and loaded
     * @param {Object} channel : channel header to add
     */
    channel_add: function(channel){
        var channel_slot = this.get_channel_slot(channel);
        var existing = this.get(channel_slot);
        if(_.contains(_.pluck(existing, 'id'), channel.id)){
            // update the old channel
            var filtered_channels = _.filter(existing, function(item){ return item.id != channel.id; });
            this.set(channel_slot, filtered_channels.concat([channel]));
        }else{
            // simply add the reveiced channel
            this.set(channel_slot, existing.concat([channel]));
        }
        // also update the flatten list
        this.channels[channel.id] = channel;

        // update the mapping for 'direct message' channel, and the partner list
        if(channel_slot === 'channel_direct_message'){
            var partner = channel.direct_partner[0];
            this.mapping[partner.id] = channel.id;
            this.partner_add(partner);
        }
    },
    channel_remove: function(channel_id){
        var channel = this.channels[channel_id];
        var slot = this.get_channel_slot(channel);
        this.set(slot, _.filter(this.get(slot), function(c){ return c.id !== channel_id; }));
        delete this.channels[channel_id];
    },
    /**
     * Get the channel the current user has with the given partner, and get the channel header
     * @param {Number[]} partner_ids : list of res.partner identifier
     */
    channel_get: function(partner_ids){
        var self = this;
        return this.ChannelModel.call('channel_get', [partner_ids]).then(function(channel){
            self.channel_apply(channel);
        });
    },
    /**
     * Create a channel with the given name and type, and apply it
     * @param {String} channel_name : the name of the channel
     * @param {String} privacy : the privacy of the channel (groups, public, ...)
     */
    channel_create: function(channel_name, privacy){
        var self = this;
        return this.ChannelModel.call('channel_create', [channel_name, privacy]).then(function(channel){
            self.channel_apply(channel);
        });
    },
    channel_info: function(channel_id){
        return this.ChannelModel.call('channel_info', [[channel_id]]).then(function(channels){
            return channels[0];
        });
    },
    channel_pin: function(uuid, pinned){
        return this.ChannelModel.call('channel_pin', [uuid, pinned]);
    },
    channel_join_and_get_info: function(channel_id){
        return this.ChannelModel.call('channel_join_and_get_info', [[channel_id]]);
    },
    channel_change: function(){
        var self = this;
        var current_channel_id = this.get('current_channel_id');
        // mail chat compose message (destroy and replace it)
        if (this.mail_chat_compose_message) {
            this.mail_chat_compose_message.destroy();
        }
        this.mail_chat_compose_message = new mail_thread.MailComposeMessage(this, new data.DataSetSearch(this, 'mail.channel', this.context), {
            'emoji_list': this.options.emoji_list,
            'context': _.extend(this.context, {
                'default_res_id': current_channel_id,
            }),
            'display_mode': 'chat',
        });
        if(_.isString(current_channel_id)){
            this.$('.o_mail_chat_composer_wrapper').hide();
        }else{
            this.$('.o_mail_chat_composer_wrapper').show();
        }
        this.mail_chat_compose_message.appendTo(this.$('.o_mail_chat_composer_wrapper'));
        this.mail_chat_compose_message.focus();

        // push state (the action is referred by action_manager, and no reloaded when jumping
        // channel, so update context is requried)
        this.action.context.active_id = current_channel_id;
        this.action.context.active_ids = [current_channel_id];
        web_client.action_manager.do_push_state({
            action: this.action.id,
            active_id: current_channel_id,
        });

        // update control panel
        this.cp_update();

        // fetch the messages
        return this.message_load_new().then(function(){
            // allow loading history
            self.loading_history = true;
            // if normal channel, update last message id, and unbold
            var def = $.Deferred().resolve();
            if(_.isNumber(current_channel_id)){
                def = self.ChannelModel.call('channel_seen', [[current_channel_id]]);
            }else{
                // auto treat needaction from inbox
                if(current_channel_id === 'channel_inbox' && self.chatter_needaction_auto){
                    def = self.MessageDatasetSearch._model.query(['id', 'channel_ids']).filter([['needaction', '=', true]]).all().then(function(messages){
                        // get needaction message ids
                        var message_ids = _.pluck(messages, 'id');
                        if(message_ids){
                            // call to unlink
                            self.MessageDatasetSearch._model.call('set_message_done',[message_ids]).then(function(){
                                // decrement channel items in batch
                                var flatten_channel_ids = _.flatten(_.pluck(messages, 'channel_ids'));
                                var channel_count = _.countBy(flatten_channel_ids, function(cid) {
                                  return cid;
                                });
                                _.each(_.keys(channel_count), function(cid){
                                    self.needaction_decrement([cid], channel_count[cid]);
                                });
                                // decrement the needaction top counter
                                internal_bus.trigger('mail_needaction_done', message_ids.length);
                            });
                        }
                    });
                }
            }
            def.then(function(){
                self._toggle_unread_message(current_channel_id, false, true);
                self._scroll();
            });
        });
    },
    channel_render: function(channel_slot){
        this.$('.o_mail_chat_channel_slot_' + channel_slot).replaceWith(QWeb.render("mail.chat.ChatMailThread.channels", {'widget': this, 'channel_slot': channel_slot}));
    },
    // partners
    partner_add: function(partner){
        var partners = _.filter(this.get('partners'), function(p){ return p.id != partner.id; });
        this.set('partners', partners.concat([partner]));
    },
    partner_render: function(){
        this.$('.o_mail_chat_channel_slot_partners').replaceWith(QWeb.render("mail.chat.ChatMailThread.partners", {'widget': this}));
    },
    // needaction
    needaction_increment: function(channel_ids, inc){
        var self = this;
        _.each(channel_ids, function(channel_id){
            if(self.channels[channel_id]){
                var count = (self.channels[channel_id].message_needaction_counter || 0) + (inc || 1);
                self.channels[channel_id].message_needaction_counter = count;
                self.$('.o_mail_chat_needaction[data-channel-id='+channel_id+']').html(count);
                self.$('.o_mail_chat_needaction[data-channel-id='+channel_id+']').show();
            }
        });
    },
    needaction_decrement: function(channel_ids, dec){
        var self = this;
        _.each(channel_ids, function(channel_id){
            if(self.channels[channel_id]){
                var count = (self.channels[channel_id].message_needaction_counter || 0) - (dec || 1);
                self.channels[channel_id].message_needaction_counter = count;
                self.$('.o_mail_chat_needaction[data-channel-id='+channel_id+']').html(count);
                if(count <= 0){
                    self.$('.o_mail_chat_needaction[data-channel-id='+channel_id+']').show();
                }
            }
        });
    },
    needaction_inbox_change: function(){
        var count = this.get('needaction_inbox_counter');
        var $elem = this.$('.o_mail_chat_needaction[data-channel-id="channel_inbox"]');
        $elem.html(count);
        if(count > 0){
            $elem.show();
        }else{
            $elem.hide();
        }
    },
    // from bus
    channel_receive: function(channel){
        this.channel_add(channel);
    },
    message_receive: function(message){
        var self = this;
        // if current channel should reveice message, give it to it
        if(_.contains(message.channel_ids, this.get('current_channel_id'))){
            this.message_insert([message]);
        }
        // for other message channel, get the channel if not loaded yet, and bolded them
        var other_message_channel_ids = _.without(message.channel_ids, this.get('current_channel_id'));
        var active_channel_ids = _.map(_.keys(this.channels), function(cid){
            return parseInt(cid);
        }); // integer as key of a dict is cast as string in javascript
        var channel_to_fetch = _.difference(other_message_channel_ids, active_channel_ids);
        // fetch unloaded channels and add it
        var def = $.Deferred();
        if(channel_to_fetch.length >= 1){
            def = this.ChannelModel.call("channel_info", [], {"ids" : channel_to_fetch}).then(function(channels){
                _.each(channels, function(channel){
                    self.channel_add(channel);
                });
            });
        }else{
            def.resolve([]);
        }
        // bold the channel to indicate unread messages
        def.then(function(){
            // bold channel having unread messages
            _.each(other_message_channel_ids, function(channel_id){
                self._toggle_unread_message(channel_id, true);
            });
            // auto scroll to bottom
            self._scroll();
        });
        // if needaction, then increment the label
        if(message.needaction_partner_ids && _.contains(message.needaction_partner_ids, session.partner_id)){
            this.needaction_increment(message.channel_ids || []);
        }
    },
    // utils function
    get_channel_slot: function(channel){
        if(channel.channel_type === 'channel'){
            if(channel.public === 'private'){
                return 'channel_private_group';
            }
            return 'channel_channel';
        }
        if(channel.channel_type === 'chat'){
            return 'channel_direct_message';
        }
    },
    get_current_channel_name: function(){
        var current_channel_id = this.get('current_channel_id');
        var current_channel = this.channels[current_channel_id];
        var current_channel_name = current_channel && current_channel.name || _t('Unknown');
        // virtual channel id (for inbox, or starred channel)
        if(_.isString(current_channel_id)){
            if(current_channel_id == 'channel_inbox'){
                current_channel_name = _t('Inbox');
            }
            if(current_channel_id == 'channel_starred'){
                current_channel_name = _t('Starred');
            }
        }
        return current_channel_name;
    },
    _toggle_unread_message: function(channel_id, add_or_remove, set_as_active){
        var partner_id = false;
        var inverse_mapping = _.invert(this.mapping);
        // toggle bold channel/partner item
        this.$('.o_mail_chat_sidebar .o_mail_chat_channel_item[data-channel-id="'+channel_id+'"]').toggleClass('o_mail_chat_channel_unread', add_or_remove);
        if(_.contains(_.keys(inverse_mapping), channel_id.toString())){
            partner_id = parseInt(inverse_mapping[channel_id]);
            this.$('.o_mail_chat_sidebar .o_mail_chat_partner_item[data-partner-id="'+partner_id+'"]').toggleClass('o_mail_chat_channel_unread', add_or_remove);
        }
        // set the channel/partner item as the active one
        if(set_as_active){
            this.$('.o_mail_chat_sidebar .o_mail_chat_channel_item, .o_mail_chat_sidebar .o_mail_chat_partner_item').find('a').removeClass('active');
            this.$('.o_mail_chat_sidebar .o_mail_chat_channel_item[data-channel-id="'+channel_id+'"]').find('a').addClass('active');
            if(partner_id){
                this.$('.o_mail_chat_sidebar .o_mail_chat_partner_item[data-partner-id="'+partner_id+'"]').find('a').addClass('active');
            }
        }
    },
    _scroll: function(){
        var current_channel_id = this.get('current_channel_id');
        var current_channel = this.channels[current_channel_id];
        if(_.isNumber(current_channel_id)){
            if(current_channel.seen_message_id){
                if(this.$(".o_mail_thread_message[data-message-id="+current_channel.seen_message_id+"]")){
                    this.$('.o_mail_chat_messages').scrollTop(this.$(".o_mail_thread_message[data-message-id="+current_channel.seen_message_id+"]").offset().top);
                }else{
                    this.$('.o_mail_chat_messages').scrollTop(0);
                }
            }else{
                this.$('.o_mail_chat_messages').scrollTop(this.$('.o_mail_chat_messages')[0].scrollHeight);
            }
            current_channel.seen_message_id = false;
        }else{
            this.$('.o_mail_chat_messages').scrollTop(this.$('.o_mail_chat_messages')[0].scrollHeight);
        }
    },
    /**
     * Render the messages
     * @override
     */
    message_render: function(){
        this.$('.o_mail_chat_messages_content').html(QWeb.render('mail.chat.ChatMailThread.content', {'widget': this}));
    },
    /**
     * Return the message domain for the current channel
     * @override
     */
    get_message_domain: function(){
        // default channel domain
        var current_channel_id = this.get('current_channel_id');
        var domain = [['channel_ids', 'in', current_channel_id]];
        // virtual channel id (for inbox, or starred channel)
        if(_.isString(current_channel_id)){
            if(current_channel_id == 'channel_inbox'){
                domain = [['needaction', '=', true]];
            }
            if(current_channel_id == 'channel_starred'){
                domain = [['starred', '=', true]];
            }
        }
        // add search domain
        domain = domain.concat(this.search_domain);
        return domain;
    },
});

core.action_registry.add('mail.chat.instant_messaging', ChatMailThread);


return {
    ChatMailThread: ChatMailThread,
};

});
