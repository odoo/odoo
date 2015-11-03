odoo.define('mail.ChatComposer', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Composer = Widget.extend({
    template: "mail.ChatComposer",

    events: {
        "keydown .o_composer_input": "on_keydown",
        "keyup .o_composer_input": "on_keyup",
        "change input.o_form_input_file": "on_attachment_change",
        "click .o_composer_button_send": "send_message",
        "click .o_composer_button_add_attachment": "on_click_add_attachment",
        "click .o_attachment_delete": "on_attachment_delete",
        "click .o_mention_proposition": "on_click_mention_item",
        "mouseover .o_mention_proposition": "on_hover_mention_proposition",
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            context: {},
            input_baseline: 18,
            input_max_height: 150,
            input_min_height: 28,
            mention_delimiter: '@',
            mention_min_length: 0,
            mention_typing_speed: 200,
            mention_fetch_limit: 8,
            get_channel_info: function () {},
        });
        this.context = this.options.context;
        this.get_channel_info = this.options.get_channel_info;

        // Attachments
        this.AttachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileupload_id = _.uniqueId('o_chat_fileupload');
        this.set('attachment_ids', []);

        // Mention
        this.PartnerModel = new Model('res.partner');
        this.mention_dropdown_open = false;
        this.set('mention_partners', []); // proposition of not-mention partner matching the mention_word
        this.set('mention_selected_partners', []); // contains the mention partners sorted as they appear in the input text
    },

    start: function () {
        var self = this;

        this.$attachment_button = this.$(".o_composer_button_add_attachment");
        this.$attachments_list = this.$('.o_composer_attachments_list');
        this.$mention_partner_tags = this.$('.o_composer_mentioned_partners');
        this.$mention_dropdown = this.$('.o_composer_mention_dropdown');
        this.$input = this.$('.o_composer_input');
        this.resize_input();

        // Attachments
        $(window).on(this.fileupload_id, this.on_attachment_loaded);
        this.on("change:attachment_ids", this, this.render_attachments);

        // Emoji
        this.$('.o_composer_button_emoji').popover({
            placement: 'top',
            content: function() {
                if (!self.$emojis) { // lazy rendering
                    self.$emojis = $(QWeb.render('mail.ChatComposer.emojis', {
                        emojis: chat_manager.get_emojis(),
                    }));
                    self.$emojis.filter('.o_mail_emoji').on('click', self, self.on_click_emoji_img);
                }
                return self.$emojis;
            },
            html: true,
            container: '.o_composer_emoji',
            trigger: 'focus',
        });

        // Mention
        this.on('change:mention_partners', this, this.render_mention_partners);
        this.on('change:mention_selected_partners', this, this.render_mention_selected_partners);
        return this._super();
    },

    preprocess_message: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer
        var value = this.$input.val().replace(/\n|\r/g, '<br/>');
        return $.when({
            content: this.mention_preprocess_message(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.pluck(this.get('mention_selected_partners'), 'id'),
        });
    },

    send_message: function () {
        if (this.is_empty() || !this.do_check_attachment_upload()) {
            return;
        }

        var self = this;
        this.preprocess_message().then(function (message) {
            self.trigger('post_message', message);

            // Empty input, selected partners and attachments
            self.$input.val('');
            self.resize_input();
            self.set('mention_selected_partners', []);
            self.set('attachment_ids', []);

            self.$input.focus();
        });
    },

    /**
     * Resizes the textarea according to its scrollHeight
     * @param {Boolean} [force_resize] if not true, only reset the size if empty
     */
    resize_input: function (force_resize) {
        if (this.$input.val() === '') {
            this.$input.css('height', this.options.input_min_height);
        } else if (force_resize) {
            var height = this.$input.prop('scrollHeight') + this.options.input_baseline;
            this.$input.css('height', Math.min(this.options.input_max_height, height));
        }
    },

    // Events
    on_click_add_attachment: function () {
        this.$('input.o_form_input_file').click();
        this.$input.focus();
    },

    on_click_emoji_img: function(event) {
        this.$input.val(this.$input.val() + " " + $(event.currentTarget).data('emoji') + " ");
        this.$input.focus();
    },

    /**
     * Send the message on ENTER, but go to new line on SHIFT+ENTER
     */
    prevent_send: function (event) {
        return event.shiftKey;
    },

    on_keydown: function (event) {
        switch(event.which) {
            // UP, DOWN: prevent moving cursor if navigation in mention propositions
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                if (this.mention_dropdown_open) {
                    event.preventDefault();
                }
                break;
            // BACKSPACE, DELETE: check if need to remove a mention
            case $.ui.keyCode.BACKSPACE:
            case $.ui.keyCode.DELETE:
                this.mention_check_remove();
                break;
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if (this.mention_dropdown_open) {
                    event.preventDefault();
                } else if (!this.prevent_send(event)) {
                    event.preventDefault();
                    this.send_message();
                } else {
                    this.resize_input(true);
                }
                break;
        }
    },

    on_keyup: function (event) {
        switch(event.which) {
            // ESCAPED KEYS: do nothing
            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_UP:
            case $.ui.keyCode.PAGE_DOWN:
                break;
            // ESCAPE: close mention propositions
            case $.ui.keyCode.ESCAPE:
                this.set('mention_partners', []);
                break;
            // ENTER, UP, DOWN: check if navigation in mention propositions
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                this.mention_proposition_navigation(event.which);
                break;
            // Otherwise, check if a mention is typed
            default:
                this.mention_word = this.mention_detect_delimiter();
                if (this.mention_word !== false) {
                    this.mention_word_changed();
                } else {
                    this.set('mention_partners', []); // close the dropdown
                }
                this.resize_input();
        }
    },

    // Attachments
    on_attachment_change: function(event) {
        var $target = $(event.target);
        if ($target.val() !== '') {
            var filename = $target.val().replace(/.*[\\\/]/,'');
            // if the files exits for this answer, delete the file before upload
            var attachments = [];
            for (var i in this.get('attachment_ids')) {
                if ((this.get('attachment_ids')[i].filename || this.get('attachment_ids')[i].name) === filename) {
                    if (this.get('attachment_ids')[i].upload) {
                        return false;
                    }
                    this.AttachmentDataSet.unlink([this.get('attachment_ids')[i].id]);
                } else {
                    attachments.push(this.get('attachment_ids')[i]);
                }
            }
            // submit filename
            this.$('form.o_form_binary_form').submit();
            this.$attachment_button.prop('disabled', true);

            attachments.push({
                'id': 0,
                'name': filename,
                'filename': filename,
                'url': '',
                'upload': true,
                'mimetype': '',
            });
            this.set('attachment_ids', attachments);
        }
    },
    on_attachment_loaded: function(event, result) {
        var attachment_ids = [];
        if (result.error || !result.id ) {
            this.do_warn(result.error);
            attachment_ids = _.filter(this.get('attachment_ids'), function (val) { return !val.upload; });
        } else {
            _.each(this.get('attachment_ids'), function(a) {
                if (a.filename === result.filename && a.upload) {
                    attachment_ids.push({
                        'id': result.id,
                        'name': result.name || result.filename,
                        'filename': result.filename,
                        'mimetype': result.mimetype,
                        'url': session.url('/web/content', {'id': result.id, download: true}),
                    });
                } else {
                    attachment_ids.push(a);
                }
            });
        }
        this.set('attachment_ids', attachment_ids);
        this.$attachment_button.prop('disabled', false);
    },
    on_attachment_delete: function(event){
        event.stopPropagation();
        var self = this;
        var attachment_id = $(event.target).data("id");
        if (attachment_id) {
            var attachments = [];
            _.each(this.get('attachment_ids'), function(attachment){
                if (attachment_id !== attachment.id) {
                    attachments.push(attachment);
                } else {
                    self.AttachmentDataSet.unlink([attachment_id]);
                }
            });
            this.set('attachment_ids', attachments);
        }
    },
    do_check_attachment_upload: function () {
        if (_.find(this.get('attachment_ids'), function (file) { return file.upload; })) {
            this.do_warn(_t("Uploading error"), _t("Please, wait while the file is uploading."));
            return false;
        }
        return true;
    },
    render_attachments: function() {
        this.$attachments_list.html(QWeb.render('mail.ChatComposer.Attachments', {
            attachments: this.get('attachment_ids'),
        }));
    },

    // Mention
    on_click_mention_item: function (event) {
        event.preventDefault();

        var text_input = this.$input.val();
        var partner_id = $(event.currentTarget).data('partner-id');
        var selected_partner = _.filter(_.flatten(this.get('mention_partners')), function (p) {
            return p.id === partner_id;
        })[0];

        // add the mention partner to the list
        var mention_selected_partners = this.get('mention_selected_partners');
        if (mention_selected_partners.length) { // there are already mention partners
            // get mention matches (ordered by index in the text)
            var matches = this.mention_get_match(text_input);
            var index = this.mention_get_index(matches, this.get_selection_positions().start);
            mention_selected_partners.splice(index, 0, selected_partner);
            mention_selected_partners = _.clone(mention_selected_partners);
        } else { // this is the first mentionned partner
            mention_selected_partners = mention_selected_partners.concat([selected_partner]);
        }
        this.set('mention_selected_partners', mention_selected_partners);

        // update input text, and reset dropdown
        var cursor_position = this.get_selection_positions().start;
        var text_left = text_input.substring(0, cursor_position-(this.mention_word.length+1));
        var text_right = text_input.substring(cursor_position, text_input.length);
        var text_input_new = text_left + this.options.mention_delimiter + selected_partner.name + ' ' + text_right;
        this.$input.val(text_input_new);
        this.set_cursor_position(text_left.length+selected_partner.name.length+2);
        this.set('mention_partners', []);
    },

    on_hover_mention_proposition: function (event) {
        var $elem = $(event.currentTarget);
        this.$('.o_mention_proposition').removeClass('active');
        $elem.addClass('active');
    },

    mention_proposition_navigation: function (keycode) {
        var $active = this.$('.o_mention_proposition.active');
        if (keycode === $.ui.keyCode.ENTER) { // selecting proposition
            $active.click();
        } else { // navigation in propositions
            var $to;
            if (keycode === $.ui.keyCode.DOWN) {
                $to = $active.nextAll('.o_mention_proposition').first();
            } else {
                $to = $active.prevAll('.o_mention_proposition').first();
            }
            if ($to.length) {
                $active.removeClass('active');
                $to.addClass('active');
            }
        }
    },

    /**
     * Return the text attached to the mention delimiter
     * @returns {String|false}: the text right after the delimiter or false
     */
    mention_detect_delimiter: function () {
        var options = this.options;
        var delimiter = options.mention_delimiter;
        var text_val = this.$input.val();
        var cursor_position = this.get_selection_positions().start;
        var left_string = text_val.substring(0, cursor_position);
        var search_str = text_val.substring(left_string.lastIndexOf(delimiter) - 1, cursor_position);

        return validate_keyword(search_str);

        function validate_keyword (search_str) {
            var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
            var regex_start = new RegExp(pattern, "g");
            search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
            if (regex_start.test(search_str) && search_str.length > options.mention_min_length) {
                search_str = search_str.replace(pattern, '');
                return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str.replace(delimiter, '') : false;
            }
            return false;
        }
    },

    mention_word_changed: function () {
        var self = this;
        // start a timeout to fetch partner with the current 'mention word'. The timer avoid to start
        // an RPC for each pushed key when the user is typing the partner name.
        // The 'mention_typing_speed' option should approach the time for a human to type a letter.
        clearTimeout(this.mention_fetch_timer);
        this.mention_fetch_timer = setTimeout(function () {
            self.mention_fetch_partner(self.mention_word);
        }, this.options.mention_typing_speed);
    },

    mention_fetch_partner: function (search) {
        var self = this;
        var kwargs = {
            channel: this.get_channel_info(),
            exclude: _.pluck(this.get('mention_selected_partners'), 'id'),
            limit: this.options.mention_fetch_limit,
            search: search,
        };
        this.PartnerModel.call('get_mention_suggestions', kwargs).then(function (suggestions) {
            self.set('mention_partners', suggestions);
        });
    },

    mention_check_remove: function () {
        var mention_selected_partners = this.get('mention_selected_partners');
        var partners_to_remove = [];
        var selection = this.get_selection_positions();
        var deleted_binf = selection.start;
        var deleted_bsup = selection.end;

        var matches = this.mention_get_match(this.$input.val());
        for (var i=0; i<matches.length; i++) {
            var m = matches[i];
            var m1 = m.index;
            var m2 = m.index + m[0].length;
            if (deleted_binf <= m2 && m1 < deleted_bsup) {
                partners_to_remove.push(mention_selected_partners[i]);
            }
        }
        this.set('mention_selected_partners', _.difference(mention_selected_partners, partners_to_remove));
    },

    mention_preprocess_message: function (message) {
        var partners = this.get('mention_selected_partners');
        if (partners.length) {
            var matches = this.mention_get_match(message);
            var substrings = [];
            var start_index = 0;
            for (var i=0; i<matches.length; i++) {
                var match = matches[i];
                var end_index = match.index + match[0].length;
                var partner_name = match[0].substring(1);
                var processed_text = _.str.sprintf("<a href='#' class='o_mail_redirect' data-oe-model='res.partner' data-oe-id='%s'>@%s</a>", partners[i].id, partner_name);
                var subtext = message.substring(start_index, end_index).replace(match[0], processed_text);
                substrings.push(subtext);
                start_index = end_index;
            }
            substrings.push(message.substring(start_index, message.length));
            return substrings.join('');
        }
        return message;
    },

    render_mention_partners: function () {
        if (_.flatten(this.get('mention_partners')).length) {
            this.$mention_dropdown.html(QWeb.render('mail.ChatComposer.MentionMenu', {
                suggestions: this.get('mention_partners'),
            }));
            this.$mention_dropdown
                .addClass('open')
                .find('.o_mention_proposition').first().addClass('active');
            this.mention_dropdown_open = true;
        } else {
            this.$mention_dropdown.removeClass('open');
            this.$mention_dropdown.empty();
            this.mention_dropdown_open = false;
        }
    },

    render_mention_selected_partners: function () {
        this.$mention_partner_tags.html(QWeb.render('mail.ChatComposer.MentionTags', {
            partners: this.get('mention_selected_partners'),
        }));
    },

    /**
     * Return the matches (as RexExp.exec does) for the partner mention in the input text
     * @param {String} input_text: the text to search matches
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    mention_get_match: function (input_text) {
        var self = this;
        // create the regex of all mention partner name
        var partner_names = _.pluck(this.get('mention_selected_partners'), 'name');
        var escaped_partner_names = _.map(partner_names, function (str) {
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

    mention_get_index: function (matches, cursor_position) {
        for (var i=0; i<matches.length; i++) {
            if (cursor_position <= matches[i].index) {
                return i;
            }
        }
        return i;
    },

    // Others
    get_selection_positions: function () {
        var el = this.$input.get(0);
        return el ? {start: el.selectionStart, end: el.selectionEnd} : {start: 0, end: 0};
    },

    set_cursor_position: function (pos) {
        this.$input.each(function (index, elem) {
            if (elem.setSelectionRange){
                elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
                elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
        });
    },

    is_empty: function () {
        return !this.$input.val().trim() && !this.$('.o_attachments').children().length;
    },
    focus: function () {
        this.$input.focus();
    },
});

return Composer;

});
