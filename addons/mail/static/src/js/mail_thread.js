odoo.define('mail.thread', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var time = require('web.time');
var Widget = require('web.Widget');
var session = require('web.session');
var web_client = require('web.web_client');
var mail_utils = require('mail.utils');

var _t = core._t;
var QWeb = core.qweb;


var LIMIT_MESSAGE = 20;

/**
 * Widget : Input textbox to post messages
 *
 * Input with 2 buttons to manage attachment and emoji
 *      - Attachment : upload selected attachment (one at a time) and display them below the textbox. Prevent
          posting message while uploading
 *      - Emoji : popover exposing emoji list, and append emoji shortcode to the textbox when click on emoji image
 * It triggers 'message_sent' event with the posted message, when it is sent to the server.
 */
var MailComposeMessage = Widget.extend({
    template: 'mail.ComposeMessage',
    events: {
        "keydown .o_mail_compose_message_input": "on_keydown",
        "change input.oe_form_binary_file": "on_attachment_change",
        "click .o_mail_compose_message_attachment_list .o_mail_attachment_delete": "on_attachment_delete",
        "click .o_mail_compose_message_button_attachment": 'on_click_attachment',
        "click .o_mail_compose_message_button_send": 'message_send',
    },
    /**
     * Contructor
     * @param {Object} options : the options of the MailComposeMessage
     * @param {Object[]} [options.emoji_list] : the list of emoji
     * @param {Object} options.context : the context. It should contains the default_res_id' (id of the current document).
     * @param {chat|mail} options.display_mode : the 'chat' mode will display an input, when the 'mail' mode will display a texarea.
     */
    init: function(parent, dataset, options){
        this._super.apply(this, arguments);
        this.thread_dataset = dataset;
        this.options = _.defaults(options || {}, {
            'emoji_list': {},
            'context': {},
            'display_mode': 'mail',
        });
        this.emoji_list = this.options.emoji_list;
        this.context = this.options.context;
        // attachment handeling
        this.AttachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileupload_id = _.uniqueId('o_mail_chat_fileupload');
        this.set('attachment_ids', []);
    },
    start: function(){
        var self = this;
        this.$input = this.$('.o_mail_compose_message_input');
        this.$input.focus();
        this.$attachment_button = this.$(".o_mail_compose_message_button_attachment");
        // attachments
        $(window).on(this.fileupload_id, this.on_attachment_loaded);
        this.on("change:attachment_ids", this, this.attachment_render);
        // emoji
        self.$('.o_mail_compose_message_button_emoji').popover({
            placement: 'top',
            content: function(){
                if(!self.$emoji){ // lazy rendering
                    self.$emoji = $(QWeb.render('mail.ComposeMessage.emoji', {'widget': self}));
                    self.$emoji.find('.o_mail_compose_message_emoji_img').on('click', self, self.on_click_emoji_img);
                }
                return self.$emoji;
            },
            html: true,
            container: '.o_mail_compose_message_emoji',
            trigger: 'focus',
        });
        return this._super();
    },
    // events
    on_click_attachment: function(event){
        event.preventDefault();
        this.$('input.oe_form_binary_file').click();
    },
    on_click_emoji_img: function(event){
        this.$input.val(this.$input.val() + " " + $(event.currentTarget).data('emoji')+ " ");
        this.$input.focus();
    },
    on_keydown: function(event){
        if(event.which === 13 && this.options.display_mode === 'chat') {
            this.message_send();
        }
    },
    message_send: function(){
        var $input = this.$('.o_mail_compose_message_input');
        var mes = mail_utils.get_text2html($input.val());
        if (! mes.trim() && this.do_check_attachment_upload()) {
            return;
        }
        $input.val("");
        this.message_post(mes, _.pluck(this.get('attachment_ids'), 'id'));
    },
    /**
     * Sent the message to the server to create a mail.message, using 'message_post' method
     * @param {String} body : the core of the message (html, or plaintext)
     * @param {Number[]} attachment_ids : attachment_ids linked to the message
     * @param {Object} kwargs : other parameters (in a dictionnary)
     * @returns {Deferred} resolved when the message is posted, and returning the new message id
     */
    message_post: function(body, attachment_ids, kwargs){
        var self = this;
        var values = _.defaults(kwargs || {}, {
            'body': body,
            'attachment_ids': attachment_ids || [],
            'message_type': 'comment',
            'content_subtype': 'html',
            'partner_ids': [],
            'subtype': 'mail.mt_comment',
        });
        return this.thread_dataset._model.call('message_post', [this.context.default_res_id], values).then(function(message_id){
            self.clean_attachments(); // empty attachment list
            self.trigger('message_sent', message_id);
            return message_id;
        });
    },
    // attachment business
    on_attachment_change: function(event){
        var $target = $(event.target);
        if ($target.val() !== '') {
            var filename = $target.val().replace(/.*[\\\/]/,'');
            // if the files exits for this answer, delete the file before upload
            var attachments = [];
            for (var i in this.get('attachment_ids')) {
                if ((this.get('attachment_ids')[i].filename || this.get('attachment_ids')[i].name) == filename) {
                    if (this.get('attachment_ids')[i].upload) {
                        return false;
                    }
                    this.AttachmentDataSet.unlink([this.get('attachment_ids')[i].id]);
                } else {
                    attachments.push(this.get('attachment_ids')[i]);
                }
            }
            // submit filename
            this.$('form.oe_form_binary_form').submit();
            this.$attachment_button.prop('disabled', true);

            attachments.push({
                'id': 0,
                'name': filename,
                'filename': filename,
                'url': '',
                'upload': true
            });
            this.set('attachment_ids', attachments);
        }
    },
    on_attachment_loaded: function(event, result){
        var attachment_ids = [];
        if (result.error || !result.id ) {
            this.do_warn(result.error);
            attachment_ids = _.filter(this.get('attachment_ids'), function (val) { return !val.upload; });
        }else{
            _.each(this.get('attachment_ids'), function(a){
                if (a.filename == result.filename && a.upload) {
                    attachment_ids.push({
                        'id': result.id,
                        'name': result.name || result.filename,
                        'filename': result.filename,
                        'url': session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'name', 'id': result.id}),
                    });
                }else{
                    attachment_ids.push(a);
                }
            });
        }
        this.set('attachment_ids', attachment_ids);

        // TODO JEM : understand the 2 lines below ....
        var $input = this.$('input.oe_form_binary_file');
        $input.after($input.clone(true)).remove();

        this.$attachment_button.prop('disabled', false);
    },
    on_attachment_delete: function(event){
        event.stopPropagation();
        var self = this;
        var attachment_id = $(event.target).data("id");
        if (attachment_id) {
            var attachments = [];
            _.each(this.get('attachment_ids'), function(attachment){
                if (attachment_id != attachment.id) {
                    attachments.push(attachment);
                } else {
                    self.AttachmentDataSet.unlink([attachment_id]);
                }
            });
            this.set('attachment_ids', attachments);
        }
    },
    do_check_attachment_upload: function () {
        if (_.find(this.get('attachment_ids'), function (file) {return file.upload;})) {
            this.do_warn(_t("Uploading error"), _t("Please, wait while the file is uploading."));
            return false;
        }
        return true;
    },
    clean_attachments: function(){
        this.set('attachment_ids', []);
    },
    // ui
    attachment_render: function(){
        this.$('.o_mail_compose_message_attachment_list').html(QWeb.render('mail.ComposeMessage.attachments', {'widget': this}));
    },
    focus: function(){
        this.$input.focus();
    }
});


/**
 * Mail Thread Mixin : Messages Managment
 *
 * Load, Fetch, Display mail.message
 * This is a mixin since it will be inherit by a form_common.AbstractField and a Wigdet (Client Action)
 *
 * @mixin
 **/
var MailThreadMixin = {
    /**
     * Constructor of the 'mail_thread' mixin
     * @param {Boolean} [options.display_log_button] : display of the 'log a note' button
     * @param {Boolean} [options.display_document_link] : display document link on message
     * @param {Boolean} [options.display_needaction_button] : display the needaction 'check' button on messages
     * @param {Object[]} [options.internal_subtypes]: list of internal subtype (for employee only)
     * @param {Object[]} [options.emoji_list] : list of emoji
     */
    init: function(){
        this.MessageDatasetSearch = new data.DataSetSearch(this, 'mail.message');
        this.set('messages', []);
        this.emoji_substitution = {};
        // options
        this.options = _.defaults(this.options || {}, {
            'display_log_button': false,
            'display_document_link': false,
            'display_needaction_button': false,
            'internal_subtypes': [],
            'emoji_list': [],
        });
    },
    start: function(){
        this.on("change:messages", this, this.message_render);
    },
    // Common Actions (They should be bind on the implementing widget, the 'events' dict)
    /**
     * Generic redirect action : redirect to the form view if the
     * click node contains 'data-oe-model' and 'data-oe-id'.
     */
    on_click_redirect: function(event){
        event.preventDefault();
        var res_id = $(event.target).data('oe-id');
        var res_model = $(event.target).data('oe-model');
        web_client.action_manager.do_push_state({
            'model': res_model,
            'id': res_id,
            'title': this.record_name,
        });
        this.do_action({
            type:'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: res_model,
            views: [[false, 'form']],
            res_id: res_id,
        }, {
            'on_reverse_breadcrumb': this.on_reverse_breadcrumb,
        });
    },
    /**
     * Will be called when clicking on the Breadcrumb (mainly of client action)
     * Need to be override
     */
    on_reverse_breadcrumb: function(){

    },
    /**
     * Toggle a message as 'starred' (or not), by toggling the 'o_mail_message_starred' css class.
     * Trigger when clicking on selector '.o_mail_thread_message_star'.
     */
    on_message_star: function(event){
        var $source = this.$(event.currentTarget);
        var mid = $source.data('message-id');
        var is_starred = !$source.hasClass('o_mail_message_starred');
        return this.MessageDatasetSearch.call('set_message_starred', [[mid], is_starred]).then(function(res){
            $source.toggleClass('o_mail_message_starred');
            return mid;
        });
    },
    on_message_needaction: function(event){
        var $source = this.$(event.currentTarget);
        var mid = $source.data('message-id');
        return this.MessageDatasetSearch.call('set_message_done', [[mid]]).then(function(res){
            $source.remove();
            return mid;
        });
    },
    // Message functions
    /**
     * Fetch given message
     * @param  {Number[]} message_ids : list of mail.message identifiers to fetch
     * @returns {Deferred} resolved when the messages are loaded
     */
    message_format: function(message_ids){
        return this.MessageDatasetSearch._model.call('message_format', [message_ids]);
    },
    /**
     * Fetch mail.message in the format defined server side
     * @param {Array} domain : Odoo Domain of the message to fetch
     * @param {Number} limit : the limit of messages to fetch
     * @returns {Deferred} resolved when the messages are loaded
     */
    message_fetch: function(domain, limit){
        domain = domain || this.get_message_domain();
        limit = limit || LIMIT_MESSAGE;
        return this.MessageDatasetSearch._model.call('message_fetch', [domain], {limit: limit});
    },
    _message_replace: function(messages){
        this.set('messages', this._message_order(messages));
    },
    /**
     * Order the message in a particular order, to be defined by implementation
     * @param {Object[]} messages : messages to order
     */
    _message_order: function(messages){
        return _.sortBy(messages, 'date');
    },
    /**
     * Insert messages in the current list
     * @param {Object[]} messages : list of mail.message (formatted server side)
     */
    message_insert: function(raw_messages){
        var current_messages = this.get('messages');
        current_messages = current_messages.concat(this._message_preprocess(raw_messages));
        this._message_replace(current_messages);
    },
    /**
     * Load history of message, with the 'history' domain, and insert them in the current list
     * @returns {Deferred} resolved when the messages are fetched and returning the raw
     *                     messages (formatted server side)
     */
    message_load_history: function(){
        var self = this;
        return this.message_fetch(this.get_message_domain_history()).then(function(raw_messages){
            self.message_insert(raw_messages);
            return raw_messages
        });
    },
    /**
     * Load messages according to the current domain, and set that new list as current messages,
     * erasing the old ones.
     * @returns {Deferred} resolved when the messages are fetched and returning the raw
     *                     messages (formatted server side)
     */
    message_load_new: function(){
        var self = this;
        return this.message_fetch(this.get_message_domain()).then(function(raw_messages){
            self._message_replace(self._message_preprocess(raw_messages));
            return raw_messages
        });
    },
    /**
     * Preprocess the list of messages before rendering, add 'computed' field (is_needaction,
     * is_starred, ...), and apply image shortcode to the message body.
     * @param {Object[]} messages : list of raw mail.message (formatted server side)
     * @returns list of messages. It can be sorted, grouped, ...
     */
    _message_preprocess: function(messages){
        var self = this;
        _.each(messages, function(m){
            m.is_needaction = _.contains(m.needaction_partner_ids, session.partner_id);
            m.is_starred = _.contains(m.starred_partner_ids, session.partner_id);
            m.date = moment(time.str_to_datetime(m.date)).format('YYYY-MM-DD HH:mm:ss'); // set the date in the correct browser user timezone
            if(m.body){
                m.body = mail_utils.shortcode_apply(m.body, self.emoji_substitution);
            }
            _.each(m.attachment_ids, function(a){
                a.url = mail_utils.get_attachment_url(session, m.id, a.id);
            });
        });
        return _.sortBy(messages, 'date');
    },
    /**
     * Take the current messages, render them, and insert the rendering in the DOM.
     * This is triggered when the mesasge list change.
     * Must be redefined, since it depends on the complete DOM widget
     */
    message_render: function(){

    },
    // Message Domains
    /**
     * Return the current domain to fetch the message of the thread. this should
     * be redifined by the thread implementation.
     */
    get_message_domain: function(){
        return [];
    },
    get_message_domain_history: function(){
        return this.get_message_domain().concat([['id', '<', _.min(_.pluck(this.get('messages'), 'id'))]]);
    },
    // Others
    /**
     * Set the list of emoji to be substituted in message body
     * @param {Object[]} emoji_list : list of emoji Object
     */
    emoji_set_substitution: function(emoji_list){
        this.emoji_substitution = mail_utils.shortcode_substitution(emoji_list);
    },
};


return {
    MailComposeMessage: MailComposeMessage,
    MailThreadMixin: MailThreadMixin,
    LIMIT_MESSAGE: LIMIT_MESSAGE,
}


});
