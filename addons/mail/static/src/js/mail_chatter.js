odoo.define('mail.chatter', function (require) {
"use strict";

var core = require('web.core');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var form_common = require('web.form_common');
var SystrayMenu = require('web.SystrayMenu');
var mail_utils = require('mail.utils');
var mail_thread = require('mail.thread');

var QWeb = core.qweb;
var _t = core._t;
var internal_bus = core.bus;


/**
 * Mail Compose Message for Chatter
 *
 * Extends the basic MailComposeMessage Widget to add 'suggested partner' layer (open popup
 * when suggested partner is selected without email, or other informations), and the button
 * to open the 'mail.compose.message' wizard.
 **/
var ChatterMailComposeMessage = mail_thread.MailComposeMessage.extend({
    template: 'mail.chatter.ComposeMessage',
    init: function(parent, dataset, options){
        this._super.apply(this, arguments);
        this.suggested_partners = [];
        this.context = options.context || {};
        this.options = _.defaults(options, {
            'record_name': false,
            'is_log': false,
            'internal_subtypes': [],
        });
        this.events = _.extend(this.events, {
            'click .o_mail_compose_message_button_full_message': 'on_compose_message',
        });
    },
    willStart: function(){
        if(this.options.is_log){
            return this._super.apply(this, arguments);
        }
        return $.when(this._super.apply(this, arguments), this.message_get_suggested_recipients());
    },
    start: function(){
        this.$input = this.$('.o_mail_compose_message_input');
        autosize(this.$input);
        this.$input.focus();
        return this._super.apply(this, arguments);
    },
    message_get_suggested_recipients: function(){
        var self = this;
        var email_addresses = _.pluck(this.suggested_partners, 'email_address');
        return this.thread_dataset.call('message_get_suggested_recipients', [[this.context.default_res_id], this.context]).done(function (suggested_recipients) {
            var thread_recipients = suggested_recipients[self.context.default_res_id];
            _.each(thread_recipients, function (recipient) {
                var parsed_email = mail_utils.parse_email(recipient[1]);
                if (_.indexOf(email_addresses, parsed_email[1]) == -1) {
                    self.suggested_partners.push({
                        'checked': true,
                        'partner_id': recipient[0],
                        'full_name': recipient[1],
                        'name': parsed_email[0],
                        'email_address': parsed_email[1],
                        'reason': recipient[2],
                    });
                }
            });
        });
    },
    /**
     * Get the list of selected suggested partner
     * @returns Array() : list of 'recipient' selected partner (may not be created in db)
     **/
    get_checked_suggested_partners: function(){
        var self = this;
        var checked_partners = [];
        this.$('.o_mail_chatter_compose_message_suggested_partners input:checked').each(function(){
            var $input = $(this);
            var full_name = $input.data('fullname');
            checked_partners = checked_partners.concat(_.filter(self.suggested_partners, function(item){
                return full_name === item.full_name;
            }));
        });
        return checked_partners;
    },
    /**
     * Check the additionnal partners (not necessary registered partners), and open a popup form view
     * for the ones who informations is missing.
     * @param Array : list of 'recipient' partners to complete informations or validate
     * @returns Deferred resolved with the list of checked suggested partners (real partner)
     **/
    check_suggested_partners: function (checked_suggested_partners) {
        var self = this;
        var check_done = $.Deferred();

        var recipients = _.filter(checked_suggested_partners, function (recipient) { return recipient.checked; });
        var recipients_to_find = _.filter(recipients, function (recipient) { return (! recipient.partner_id); });
        var names_to_find = _.pluck(recipients_to_find, 'full_name');
        var recipients_to_check = _.filter(recipients, function (recipient) { return (recipient.partner_id && ! recipient.email_address); });
        var recipient_ids = _.pluck(_.filter(recipients, function (recipient) { return recipient.partner_id && recipient.email_address; }), 'partner_id');

        var names_to_remove = [];
        var recipient_ids_to_remove = [];

        // have unknown names -> call message_get_partner_info_from_emails to try to find partner_id
        var find_done = $.Deferred();
        if (names_to_find.length > 0) {
            find_done = self.thread_dataset.call('message_partner_info_from_emails', [[this.context.default_res_id], names_to_find]);
        } else {
            find_done.resolve([]);
        }

        // for unknown names + incomplete partners -> open popup - cancel = remove from recipients
        $.when(find_done).pipe(function (result) {
            var emails_deferred = [];
            var recipient_popups = result.concat(recipients_to_check);

            _.each(recipient_popups, function (partner_info) {
                var deferred = $.Deferred();
                emails_deferred.push(deferred);

                var partner_name = partner_info.full_name;
                var partner_id = partner_info.partner_id;
                var parsed_email = mail_utils.parse_email(partner_name);

                var pop = new form_common.FormViewDialog(this, {
                    res_model: 'res.partner',
                    res_id: partner_id,
                    context: {
                        'force_email': true,
                        'ref': "compound_context",
                        'default_name': parsed_email[0],
                        'default_email': parsed_email[1],
                    },
                    title: _t("Please complete partner's informations"),
                }).open();
                pop.on('closed', self, function () {
                    deferred.resolve();
                });
                pop.view_form.on('on_button_cancel', self, function () {
                    names_to_remove.push(partner_name);
                    if (partner_id) {
                        recipient_ids_to_remove.push(partner_id);
                    }
                });
            });
            $.when.apply($, emails_deferred).then(function () {
                var new_names_to_find = _.difference(names_to_find, names_to_remove);
                find_done = $.Deferred();
                if (new_names_to_find.length > 0) {
                    find_done = self.thread_dataset.call('message_partner_info_from_emails', [[self.context.default_res_id], new_names_to_find, true]);
                } else {
                    find_done.resolve([]);
                }
                $.when(find_done).pipe(function (result) {
                    var recipient_popups = result.concat(recipients_to_check);
                    _.each(recipient_popups, function (partner_info) {
                        if (partner_info.partner_id && _.indexOf(partner_info.partner_id, recipient_ids_to_remove) == -1) {
                            recipient_ids.push(partner_info.partner_id);
                        }
                    });
                }).pipe(function () {
                    check_done.resolve(recipient_ids);
                });
            });
        });
        return check_done;
    },
    message_post: function(body, attachment_ids, values){
        var self = this;
        var _super = self._super;
        // default values
        values = _.defaults(values || {}, {
            'message_type': 'comment',
            'content_subtype': 'html',
            'partner_ids': [],
            'subtype_id': false,
            'subtype': false,
        });
        // update subtype
        if(this.options.is_log) {
            var subtype_id = parseInt(this.$('.o_mail_chatter_compose_message_subtype_select').val());
            if(_.indexOf(_.pluck(this.internal_subtypes, 'id'), subtype_id) == -1) {
                values.subtype = 'mail.mt_note';
            }else{
                values.subtype_id = subtype_id;
            }
        }else{
            values.subtype = 'mail.mt_comment';
        }
        // update partner_ids
        var def = $.when();
        if(this.options.is_log){
            // directly call the super()
            def = _.bind(_super, self)(body, attachment_ids, values);
        }else{
            // call the super() when all partner popup are treated
            var checked_suggested_partners = this.get_checked_suggested_partners();
            this.check_suggested_partners(checked_suggested_partners).done(function(partner_ids){
                // update context
                values.partner_ids = partner_ids;
                values.context = _.defaults(self.context, {
                    'mail_post_autofollow': true,
                    'mail_post_autofollow_partner_ids': partner_ids,
                });
                def = _.bind(_super, self)(body, attachment_ids, values);
            });
        }
        return def;
    },
    is_empty: function(){
        return this.$input.val() === '';
    },
    on_compose_message: function(){
        var self = this;
        if (!this.do_check_attachment_upload()){
            return false;
        }

        var recipient_done = $.Deferred();
        if (this.options.is_log){
            recipient_done.resolve([]);
        }else{
            var checked_suggested_partners = this.get_checked_suggested_partners();
            recipient_done = this.check_suggested_partners(checked_suggested_partners);
        }
        recipient_done.then(function(partner_ids){
            var context = {
                'default_parent_id': self.id,
                'default_body': mail_utils.get_text2html(self.$('.o_mail_compose_message_input').val()),
                'default_attachment_ids': _.pluck(self.get('attachment_ids'), 'id'),
                'default_partner_ids': partner_ids,
                'default_is_log': self.options.is_log,
                'mail_post_autofollow': true,
                'mail_post_autofollow_partner_ids': partner_ids,
            };

            if (self.context.default_model && self.context.default_res_id) {
                context.default_model = self.context.default_model;
                context.default_res_id = self.context.default_res_id;
            }

            self.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            }, {
                on_close: function() {
                    self.trigger('need_refresh');
                },
            });
        });
    }
});


/**
 * Document Chatter ('mail_thread' widget)
 *
 * Displayed on every document. Since it is displayed on a form view, it extends 'AbstractField' widget, and
 * required the behaviour of 'MailThreadMixin' to manage mail.message (using common methods).
 * This widget is responsible of the toggle the message composer and the custom message rendering.
 **/
var ChatterMailThread = form_common.AbstractField.extend(mail_thread.MailThreadMixin, {
    template: 'mail.chatter.ChatterMailThread',
    events: {
        "click .o_mail_redirect": "on_click_redirect",
        "click .o_mail_thread_message_star": "on_message_star",
        "click .o_mail_thread_message_needaction": "on_message_needaction",
        "click .o_mail_thread_show_more": "message_load_history",
        // toggle message composer (!! declaration order is important !!)
        "click .o_mail_chatter_button_new_message": "on_open_composer",
        "click .o_mail_chatter_button_log_note": "on_open_composer",
        "blur .o_mail_compose_message_input": "on_close_composer",
        "mousedown .o_mail_chatter_compose_message": function() {
            this.stay_open = true;
        },
        "focus .o_mail_compose_message_input": function() {
            this.stay_open = false;
        },
        "keydown .o_mail_compose_message_input": function() {
            this.stay_open = false;
        },
    },
    init: function (){
        this._super.apply(this, arguments);
        mail_thread.MailThreadMixin.init.call(this);
        this.message_composer = undefined;
        this.record_name = '';
        this.context = this.options.context || {};
        // options from 'message_ids' node in field_view_get
        this.options = _.defaults(this.options, {
            'display_log_button': true,
            'display_document_link': false,
            'internal_subtypes': [],
            'emoji_list': [],
        });
        this.emoji_set_substitution(this.options.emoji_list);
    },
    start: function(){
        mail_thread.MailThreadMixin.start.call(this);
        return this._super.apply(this, arguments);
    },
    /**
     * When a message is correctly posted, fetch its data to render it
     * @param {Number} message_id : the identifier of the new posted message
     * @returns {Deferred}
     */
    on_message_post: function(message_id){
        var self = this;
        return this.message_format([message_id]).then(function(messages){
            self.stay_open = false;
            self.message_insert(messages);
            self.on_close_composer();
        });
    },
    /**
     * The value of the field has change (modification or switch to next document). Form view is
     * not re-rendered, simply updated. A re-fetch is needed.
     * @override
     */
    render_value: function(){
        var self = this;
        // re-rendering for mail composer message
        this.all_messages_loaded = this.get_value().length <= mail_thread.LIMIT_MESSAGE;
        this.renderElement();
        // reset dataset
        this.ThreadDataset = this.view.dataset;
        // update context (require for mail.compose.message wizard)
        this.context = _.extend({
            'mail_read_set_read': true,  // set messages as read in Chatter TODO JEM : not used anymore
            'default_res_id': this.view.datarecord.id || false,
            'default_model': this.view.model || false,
        }, this.options.context || {});
        // fetch messages of current document
        var ids = this.get_value() || [];
        return this.message_format(ids.slice(0, mail_thread.LIMIT_MESSAGE)).then(function(raw_messages){
            self._message_replace(self._message_preprocess(raw_messages));
            self.record_name = _.last(raw_messages) ? _.last(raw_messages).record_name : '';
            // set the thread as read
            self.ThreadDataset.call('message_set_read', [[self.view.datarecord.id]]).then(function(message_ids){
                // decrement the needaction top counter
                internal_bus.trigger('mail_needaction_done', message_ids.length);
            });
        });
    },
    // composer toggle
    on_open_composer: function(event){
        var self = this;
        this.$('.o_mail_chatter_compose_message').show();
        // destroy existing composer
        if(this.message_composer){
            this.message_composer.destroy();
        }
        // create the new composer
        this.message_composer = new ChatterMailComposeMessage(this, this.ThreadDataset, {
            'internal_subtypes': this.options.internal_subtypes,
            'is_log': this.$(event.currentTarget).hasClass('o_mail_chatter_button_log_note'),
            'emoji_list': this.options.emoji_list,
            'context': this.context,
            'record_name': this.record_name,
        });
        this.message_composer.appendTo(this.$('.o_mail_chatter_compose_message'));
        this.message_composer.on('message_sent', this, this.on_message_post);
        this.message_composer.on('need_refresh', this, function(){
            self.message_refresh();
            self.on_close_composer();
        });
    },
    on_close_composer: function(){
        if(this.message_composer && this.message_composer.is_empty() && !this.stay_open){
            this.$('.o_mail_chatter_compose_message').hide();
        }
    },
    /**
     * Refresh the current message, and set them as current message. Use 'message_fetch', since its
     * domain don't use 'ids', so if there is new messages, they'll be fetched.
     * @returns {Deferred}
     */
    message_refresh: function(){
        return this.message_load_new();
    },
    /**
     * Render the messages
     * @override
     */
    message_render: function(){
        this.$('.o_mail_chatter_messages').html(QWeb.render('mail.chatter.ChatterMailThread.messages', {'widget': this}));

        // display image thumbnail
        this.$(".o_mail_chatter_messages .o_image[data-mimetype^='image']").each(function () {
            var $img = $(this);
            if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
                $img.css('background-image', "url('" + $img.data('src') + "')");
            }
        });
    },
    /**
     * Order the messages
     * @param {Object[]} messages : messages to order
     * @override
     */
    _message_order: function(messages){
        messages = mail_thread.MailThreadMixin._message_order.call(this, messages);
        return messages.reverse();
    },
    /**
     * Return the message domain for the current document mail thread
     * @override
     */
    get_message_domain: function(){
        var res_id = this.ThreadDataset.ids[this.ThreadDataset.index];
        return [['model', '=', this.ThreadDataset.model], ['res_id', '=', res_id]];
    }
});

core.form_widget_registry.add('mail_thread', ChatterMailThread);



/**
 * Global ComposeMessage Top Button
 *
 * Add a link on the top user bar to write a full mail. It opens the form view
 * of the mail.compose.message (in a modal).
 */
var ComposeMessageTopButton = Widget.extend({
    template:'mail.ComposeMessageTopButton',
    events: {
        "click": "on_compose_message",
    },
    on_compose_message: function (ev) {
        ev.preventDefault();
        web_client.action_manager.do_action({
            type: 'ir.actions.act_window',
            res_model: 'mail.compose.message',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    },
});

// Put the ComposeMessageTopButton widget in the systray menu
SystrayMenu.Items.push(ComposeMessageTopButton);


return {
    ChatterMailThread: ChatterMailThread,
};

});
