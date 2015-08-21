odoo.define('mail.thread', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
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
        "keyup .o_mail_compose_message_input": "on_keyup",
        "change input.oe_form_binary_file": "on_attachment_change",
        "click .o_mail_compose_message_attachment_list .o_mail_attachment_delete": "on_attachment_delete",
        "click .o_mail_compose_message_button_attachment": 'on_click_attachment',
        "click .o_mail_compose_message_button_send": 'message_send',
        "click .o_mail_mention_proposition": "on_click_mention_item",
        "mouseover .o_mail_mention_proposition": "on_hover_mention_proposition",
    },
    /**
     * Contructor
     * @param {Object} options : the options of the MailComposeMessage
     * @param {Object[]} [options.emoji_list] : the list of emoji
     * @param {Object} options.context : the context. It should contains the default_res_id' (id of the current document).
     * @param {chat|mail} options.display_mode : the 'chat' mode will display an input, when the 'mail' mode will display a texarea.
     * @param {Char} [options.mention_delimiter] : the delimiter char to distinguish the beginning of a mention
     * @param {Integer} [options.mention_min_length] : min length of the mention word required to start a search on partner
     * @param {Integer} [options.mention_typing_speed] : delay before starting a search with the mention word
     * @param {Integer} [options.mention_fetch_limit] : limit of partner fetch
     * @param {top|bottom} [options.mention_menu_orientation] : orientation of the dropdown menu regarding the input text
     */
    init: function(parent, dataset, options){
        this._super.apply(this, arguments);
        this.thread_dataset = dataset;
        this.options = _.defaults(options || {}, {
            'emoji_list': {},
            'context': {},
            'display_mode': 'mail',
            'mention_delimiter': '@',
            'mention_min_length': 2,
            'mention_typing_speed': 400,
            'mention_fetch_limit': 8,
            'mention_menu_orientation': 'top',
        });
        this.emoji_list = this.options.emoji_list;
        this.context = this.options.context;
        this.input_buffer = ''; // save the value at keydown
        // attachment handeling
        this.AttachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileupload_id = _.uniqueId('o_mail_chat_fileupload');
        this.set('attachment_ids', []);
        // mention
        this.PartnerModel = new Model('res.partner');
        this.set('mention_word', false); // word typed after the delimiter
        this.set('mention_partners', []); // proposition of not-mention partner matching the mention_word
        this.set('mention_selected_partners', []); // contains the mention partners sorted as they appear in the input text
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
        // mention
        this.on('change:mention_word', this, this.mention_word_change);
        this.on('change:mention_partners', this, this.mention_render_partner);
        this.on('change:mention_selected_partners', this, this.mention_render_selected_partners);
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

                // Save the old input
        this.input_buffer = this.$input.val();
        // Key Down displatching
        switch(event.which) {
            // BACKSPACE : check if need to remove a mention
            case $.ui.keyCode.BACKSPACE:
                this.mention_check_remove(event.which);
                break;
            // ENTER : submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if(!this.get('mention_partners').length && this.options.display_mode === 'chat'){
                    this.message_send();
                }
                break;
        }
    },
    message_send: function(){
        var $input = this.$('.o_mail_compose_message_input');
        var mes = mail_utils.get_text2html(this.$input.val());
        if (! mes.trim() && this.do_check_attachment_upload()) {
            return;
        }
        $input.val("");
        this.message_post(mes, _.pluck(this.get('attachment_ids'), 'id'));
    },
    on_keyup: function(event){
        switch(event.which) {
            // ESCAPED KEYS : do nothing
            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_UP:
            case $.ui.keyCode.PAGE_DOWN:
            case $.ui.keyCode.ESCAPE:
                // do nothing
                break;
            // ENTER, UP, DOWN : check if navigation in mention propositions
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.ENTER:
                this.mention_proposition_navigation(event.which);
                break;
            // DELETE : check if need to remove a mention
            case $.ui.keyCode.DELETE:
                this.mention_check_remove(event.which);
                break;
            // Otherwise, check is a mention is typed
            default:
                var mention_word = this.mention_detect_delimiter();
                if(mention_word){
                    this.set('mention_word', mention_word);
                }else{
                    this.set('mention_partners', []); // close the dropdown
                }
        }
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
            'message_type': 'comment',
            'content_subtype': 'html',
            'partner_ids': [],
            'subtype': 'mail.mt_comment',
        });
        values = _.extend(values, {
            'body': this.mention_preprocess_message(body),
            'attachment_ids': attachment_ids || [],
            'partner_ids': _.pluck(this.get('mention_selected_partners'), 'id').concat(values.partner_ids),
        });
        return this.thread_dataset._model.call('message_post', [this.context.default_res_id], values).then(function(message_id){
            self.reset(); // empty attachment, mention partners, ...
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
    attachment_render: function(){
        this.$('.o_mail_compose_message_attachment_list').html(QWeb.render('mail.ComposeMessage.attachments', {'widget': this}));
    },
    // Mention
    on_click_mention_item: function(event){
        event.preventDefault();

        var text_input = this.$input.val();
        var partner_id = this.$(event.currentTarget).data('partner-id');
        var selected_partner = _.filter(this.get('mention_partners'), function(p){
            return p.id === partner_id;
        })[0];

        // add the mention partner to the list
        var mention_selected_partners = this.get('mention_selected_partners');
        if(mention_selected_partners.length){ // there are already mention partner
            // get mention matches (ordered by index in the text)
            var matches = this.mention_get_match(text_input);
            var index = this.mention_get_index(matches, this.get_cursor_position());
            mention_selected_partners.splice(index, 0, selected_partner);
            mention_selected_partners = _.clone(mention_selected_partners);
        }else{ // this is the first mentionned partner
            mention_selected_partners = mention_selected_partners.concat([selected_partner]);
        }
        this.set('mention_selected_partners', mention_selected_partners);

        // update input text, and reset dropdown
        var mention_word = this.get('mention_word');
        var cursor_position = this.get_cursor_position();
        var text_left = text_input.substring(0, cursor_position-(mention_word.length+1));
        var text_right = text_input.substring(cursor_position, text_input.length);
        var text_input_new = text_left + this.options.mention_delimiter + selected_partner.name + ' ' + text_right;

        this.$input.val(text_input_new);
        this.set_cursor_position(text_left.length+selected_partner.name.length+2);
        this.set('mention_partners', []);
    },
    on_hover_mention_proposition: function(event){
        var $elem = this.$(event.currentTarget);
        this.$('.o_mail_mention_proposition').removeClass('active');
        $elem.addClass('active');
    },
    mention_proposition_navigation: function(keycode){
        var $active = this.$('.o_mail_mention_proposition.active');
        if(keycode === $.ui.keyCode.ENTER){ // selecting proposition
            if($active){
                $active.click();
            }
        }else{ // navigation in propositions
            var $to;
            if(keycode === $.ui.keyCode.DOWN){
                $to = $active.next('.o_mail_mention_proposition:not(.active)');
            }else{
                $to = $active.prev('.o_mail_mention_proposition:not(.active)');
            }
            if($to.length){
                this.$('.o_mail_mention_proposition').removeClass('active');
                $to.addClass('active');
            }
        }
    },
    /**
     * Return the text attached to the mention delimiter
     * @returns {String|false} : the text right after the delimiter or false
     */
    mention_detect_delimiter: function(){
        var self = this;
        var delimiter = self.options.mention_delimiter;
        var validate_keyword = function(search_str){
            var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
            var regex_start = new RegExp(pattern, "g");
            search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
            if (regex_start.test(search_str) && search_str.length > self.options.mention_min_length){
                search_str = search_str.replace(pattern, '');
                return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str.replace(delimiter, '') : false;
            }
            return false;
        };
        var text_val = this.$input.val();
        var left_string = text_val.substring(0, this.get_cursor_position());
        var search_str = text_val.substring(left_string.lastIndexOf(delimiter) - 1, this.get_cursor_position());
        return validate_keyword(search_str);
    },
    mention_word_change: function(){
        var self = this;
        var word = this.get('mention_word');
        if(word){
            // start a timeout to fetch partner with the current 'mention word'. The timer avoid to start
            // a RPC for each pushed key when the user is typing the partner name. The 'mention_typing_speed'
            // option should approach the time for a human to type a letter.
            clearTimeout(this.mention_fetch_timer);
            this.mention_fetch_timer = setTimeout(function() {
                self.mention_fetch_partner();
            }, this.options.mention_typing_speed);
        }else{
            // when deleting mention word, avoid RPC call with last long enough word
            clearTimeout(this.mention_fetch_timer);
        }
    },
    mention_fetch_partner: function(){
        var self = this;
        var search_str = this.get('mention_word');
        this.PartnerModel.query(['id', 'name', 'email'])
            .filter([['id', 'not in', _.pluck(this.get('mention_selected_partners'), 'id')],'|', ['name', 'ilike', search_str], ['email', 'ilike', search_str]])
            .limit(this.options.mention_fetch_limit)
            .all().then(function(partners){
                self.set('mention_partners', partners);
        });
    },
    mention_check_remove: function(keycode){
        var mention_selected_partners = this.get('mention_selected_partners');
        var cursor = this.get_cursor_position();
        var input_text = this.$input.val();
        var matches;
        switch(keycode) {
            // Remove a mention when a character belonging to a mention word is removed from the input text
            case $.ui.keyCode.BACKSPACE:
                matches = this.mention_get_match(this.$input.val());
                for(var i=0 ; i< matches.length ; i++){
                    var m = matches[i];
                    if(m.index <= cursor && cursor <= m.index+m[0].length){
                        mention_selected_partners.splice(i, 1);
                    }
                }
                break;
            // Remove a mention if the deleted string overlapse a mention
            case $.ui.keyCode.DELETE:
                var left_text = input_text.substring(0, cursor);
                var right_text = input_text.substring(cursor, input_text.length);
                var temp = this.input_buffer.substring(0, this.input_buffer.length - right_text.length);
                var deleted_text = temp.substring(left_text.length, temp.length);

                var deleted_binf = left_text.length;
                var deleted_bsup = left_text.length + deleted_text.length;

                matches = this.mention_get_match(this.input_buffer);
                for(var i=0 ; i< matches.length ; i++){
                    var m = matches[i];
                    var m1 = m.index;
                    var m2 = m.index+m[0].length;
                    if(deleted_binf <= m2 && m1 <= deleted_bsup){
                        mention_selected_partners.splice(i, 1);
                    }
                }
                break;
        }
        this.set('mention_selected_partners', _.clone(mention_selected_partners));
    },
    mention_preprocess_message: function(body){
        var partners = this.get('mention_selected_partners');
        if(partners.length){
            var matches = this.mention_get_match(body);
            var substrings = [];
            var start_index = 0;
            for(var i=0; i < matches.length ; i++){
                var match = matches[i];
                var end_index = match.index+match[0].length;
                var subtext = body.substring(start_index, end_index);
                subtext = subtext.replace(match[0], _.str.sprintf("<span data-oe-model='res.partner' data-oe-id='%s'>%s</span>", partners[i].id, match[0]));
                substrings.push(subtext);
                start_index = end_index;
            }
            substrings.push(body.substring(start_index, body.length));
            return substrings.join('');
        }
        return body;
    },
    mention_render_partner: function(){
        this.$('.o_mail_mention_dropdown').html(QWeb.render('mail.ComposeMessage.mention_menu', {'widget': this}));
        if(this.get('mention_partners').length){
            this.$('.o_mail_mention_dropdown').addClass('open');
        }else{
            this.$('.o_mail_mention_dropdown').removeClass('open');
        }
    },
    mention_render_selected_partners: function(){
        this.$('.o_mail_mention_partner_tags').html(QWeb.render('mail.ComposeMessage.mention_tags', {'widget': this}));
    },
    /**
     * Return the matches (as RexExp.exec do) for the partner mention in the input text
     * @param {String} input_text : the text to search matches
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    mention_get_match: function(input_text){
        var self = this;
        // create the regex of all mention partner name
        var partner_names = _.pluck(this.get('mention_selected_partners'), 'name');
        var escaped_partner_names = _.map(partner_names, function(str){
            return "("+_.str.escapeRegExp(self.options.mention_delimiter+str)+")";
        });
        var regex_str = escaped_partner_names.join('|');
        // extract matches
        var result = [];
        if(regex_str.length){
            var myRegexp = new RegExp(regex_str, 'g');
            var match = myRegexp.exec(input_text);
            while (match !== null) {
                result.push(match);
                match = myRegexp.exec(input_text);
            }
        }
        return result;
    },
    mention_get_index: function(matches, cursor_position){
        for(var i = 0 ; i < matches.length ; i++){
            if(cursor_position < matches[i].index){
                return i;
            }else{
                if(i === matches.length-1){
                    return i+1;
                }
            }
        }
        return 0;
    },
    // others
    reset: function(){
        this.set('attachment_ids', []);
        this.set('mention_partners', []);
        this.set('mention_selected_partners', []);
    },
    focus: function(){
        this.$input.focus();
    },
    get_cursor_position: function() {
        var el = this.$input.get(0);
        if(!el){
            return 0;
        }
        if('selectionStart' in el) {
            return el.selectionStart;
        } else if('selection' in document) {
            var cr = document.selection.createRange();
            return cr.moveStart('character', -el.focus().value.length).text.length - cr.text.length;
        }
        return 0;
    },
    set_cursor_position: function(pos) {
        this.$input.each(function(index, elem) {
            if (elem.setSelectionRange){
                elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
                elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
        });
    },
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
            'default_username': _t('Anonymous'),
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
        return this.MessageDatasetSearch.call('set_message_starred', [[mid], is_starred]).then(function(){
            $source.toggleClass('o_mail_message_starred');
            return mid;
        });
    },
    on_message_needaction: function(event){
        var $source = this.$(event.currentTarget);
        var mid = $source.data('message-id');
        return this.MessageDatasetSearch.call('set_message_done', [[mid]]).then(function(){
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
            return raw_messages;
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
            return raw_messages;
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
                m.body = self._message_preprocess_mention(m.body);
            }
            _.each(m.attachment_ids, function(a){
                a.url = mail_utils.get_attachment_url(session, m.id, a.id);
            });
        });
        return _.sortBy(messages, 'date');
    },
    /**
     * Transform the mention 'span' tag into a link tag to the partner form
     * @param {String} body : the message body (html) to transform
     * @returns {String} the transformed body
     */
    _message_preprocess_mention: function(body){
        var re = /<span data-oe-model="([^"]*)"\s+data-oe-id="([^"]*)">(.*?)\<\/span>/g;
        var subst = "<a href='#model=$1&id=$2' class='o_mail_redirect' data-oe-model='$1' data-oe-id='$2'>$3</a>";
        return body.replace(re, subst);
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
};


});
