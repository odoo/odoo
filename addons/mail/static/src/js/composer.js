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

// The MentionManager allows the Composer to register listeners. For each
// listener, it detects if the user is currently typing a mention (starting by a
// given delimiter). If so, if fetches mention suggestions and renders them. On
// suggestion clicked, it updates the selection for the corresponding listener.
var MentionManager = Widget.extend({
    className: 'dropup o_composer_mention_dropdown',

    events: {
        "mouseover .o_mention_proposition": "on_hover_mention_proposition",
        "click .o_mention_proposition": "on_click_mention_item",
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.composer = parent;
        this.options = _.extend({}, options, {
            min_length: 0,
            typing_speed: 200,
        });

        this.open = false;
        this.listeners = [];
        this.set('mention_suggestions', []);
        this.on('change:mention_suggestions', this, this._render_suggestions);
    },

    // Events
    on_hover_mention_proposition: function (event) {
        var $elem = $(event.currentTarget);
        this.$('.o_mention_proposition').removeClass('active');
        $elem.addClass('active');
    },
    on_click_mention_item: function (event) {
        event.preventDefault();

        var text_input = this.composer.$input.val();
        var id = $(event.currentTarget).data('id');
        var selected_suggestion = _.find(_.flatten(this.get('mention_suggestions')), function (s) {
            return s.id === id;
        });
        var get_mention_index = function (matches, cursor_position) {
            for (var i=0; i<matches.length; i++) {
                if (cursor_position <= matches[i].index) {
                    return i;
                }
            }
            return i;
        };

        // add the selected suggestion to the list
        var selection = this.active_listener.selection;
        if (selection.length && this.active_listener.sort_selection) {
            // get mention matches (ordered by index in the text)
            var matches = this._get_match(text_input, this.active_listener);
            var index = get_mention_index(matches, this._get_selection_positions().start);
            selection.splice(index, 0, selected_suggestion);
        } else {
            selection = selection.concat([selected_suggestion]);
        }
        this._update_listener_selection(this.active_listener, selection);

        // update input text, and reset dropdown
        var cursor_position = this._get_selection_positions().start;
        var text_left = text_input.substring(0, cursor_position-(this.mention_word.length+1));
        var text_right = text_input.substring(cursor_position, text_input.length);
        var text_input_new = text_left + this.active_listener.delimiter + selected_suggestion.name + ' ' + text_right;
        this.composer.$input.val(text_input_new);
        this._set_cursor_position(text_left.length+selected_suggestion.name.length+2);
        this.set('mention_suggestions', []);
    },

    // Public API
    /**
     * Registers a new listener, described by an object containing the following keys
     * @param {char} [delimiter] the mention delimiter
     * @param {function} [fetch_callback] the callback to fetch mention suggestions
     * @param {string} [model] the model used for redirection
     * @param {boolean} [notify_selection_changed] true to trigger an event when the selection changes
     * @param {string} [redirect_classname] the classname of the <a> wrapping the mention
     * @param {boolean} [sort_selection] true if the selection must be sorted
     * @param {string} [suggestions_template] the QWeb template to render suggestions
     */
    register: function (listener) {
        this.listeners.push(_.extend(listener, {
            selection: [],
        }));
    },

    /**
     * Returns true if the mention suggestions dropdown is open, false otherwise
     */
    is_open: function () {
        return this.open;
    },

    get_listener_selection: function (delimiter) {
        var listener = _.findWhere(this.listeners, {delimiter: delimiter});
        return listener ? listener.selection : [];
    },

    proposition_navigation: function (keycode) {
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
     * Detects if the user is currently typing a mention word
     * @return the search string if it is, false otherwise
     */
    detect_delimiter: function () {
        var self = this;
        var options = this.options;
        var text_val = this.composer.$input.val();
        var cursor_position = this._get_selection_positions().start;
        var left_string = text_val.substring(0, cursor_position);
        function validate_keyword (delimiter) {
            var search_str = text_val.substring(left_string.lastIndexOf(delimiter) - 1, cursor_position);
            var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
            var regex_start = new RegExp(pattern, "g");
            search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
            if (regex_start.test(search_str) && search_str.length > options.min_length) {
                search_str = search_str.replace(pattern, '');
                return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str.replace(delimiter, '') : false;
            }
            return false;
        }

        this.active_listener = undefined;
        for (var i=0; i<this.listeners.length; i++) {
            var listener = this.listeners[i];
            this.mention_word = validate_keyword(listener.delimiter);

            if (this.mention_word !== false) {
                this.active_listener = listener;
                break;
            }
        }

        if (this.active_listener) {
            // start a timeout to fetch data with the current 'mention word'. The timer avoid to start
            // an RPC for each pushed key when the user is still typing.
            // The 'typing_speed' option should approach the time for a human to type a letter.
            clearTimeout(this.mention_fetch_timer);
            this.mention_fetch_timer = setTimeout(function () {
                $.when(listener.fetch_callback(self.mention_word, self.active_listener)).then(function (suggestions) {
                    self.set('mention_suggestions', suggestions);
                });
            }, this.options.typing_speed);               
        } else {
            this.set('mention_suggestions', []); // close the dropdown
        }
    },

    /**
     * Checks if a listener's selection should be updated after DELETE or BACKSPACE keypress
     */
    check_remove: function () {
        var self = this;
        var to_remove = [];
        var selection = this._get_selection_positions();
        var deleted_binf = selection.start;
        var deleted_bsup = selection.end;

        _.each(this.listeners, function (listener) {
            var mention_selection = listener.selection;
            var matches = self._get_match(self.composer.$input.val(), listener);
            for (var i=0; i<matches.length; i++) {
                var m = matches[i];
                var m1 = m.index;
                var m2 = m.index + m[0].length;
                if (deleted_binf <= m2 && m1 < deleted_bsup) {
                    to_remove.push(mention_selection[i]);
                }
            }
            if (to_remove.length) {
                self._update_listener_selection(listener, _.difference(mention_selection, to_remove));
            }
        });
    },

    /**
     * Replaces mentions appearing in the string 's' by html links with proper redirection
     */
    generate_links: function (s) {
        var self = this;
        var mention_link = "<a href='#' class='%s' data-oe-id='%s' data-oe-model='%s'>%s%s</a>";
        _.each(this.listeners, function (listener) {
            var selection = listener.selection;
            if (selection.length) {
                var matches = self._get_match(s, listener);
                var substrings = [];
                var start_index = 0;
                for (var i=0; i<matches.length; i++) {
                    var match = matches[i];
                    var end_index = match.index + match[0].length;
                    var match_name = match[0].substring(1);
                    var processed_text = _.str.sprintf(mention_link, listener.redirect_classname, selection[i].id, listener.model, listener.delimiter, match_name);
                    var subtext = s.substring(start_index, end_index).replace(match[0], processed_text);
                    substrings.push(subtext);
                    start_index = end_index;
                }
                substrings.push(s.substring(start_index, s.length));
                s = substrings.join('');
            }
        });
        return s;
    },

    reset_selections: function () {
        var self = this;
        _.each(this.listeners, function (listener) {
            self._update_listener_selection(listener, []);
        });
    },

    // Private functions
    /**
     * Returns the matches (as RexExp.exec does) for the mention in the input text
     * @param {String} input_text: the text to search matches
     * @param {Object} listener: the listener for which we want to find a match
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    _get_match: function (input_text, listener) {
        // create the regex of all mention's names
        var names = _.pluck(listener.selection, 'name');
        var escaped_names = _.map(names, function (str) {
            return "("+_.str.escapeRegExp(listener.delimiter+str)+")";
        });
        var regex_str = escaped_names.join('|');
        // extract matches
        var result = [];
        if (regex_str.length) {
            var myRegexp = new RegExp(regex_str, 'g');
            var match = myRegexp.exec(input_text);
            while (match !== null) {
                result.push(match);
                match = myRegexp.exec(input_text);
            }
        }
        return result;
    },
    _render_suggestions: function () {
        if (_.flatten(this.get('mention_suggestions')).length) {
            this.$el.html(QWeb.render(this.active_listener.suggestions_template, {
                suggestions: this.get('mention_suggestions'),
            }));
            this.$el
                .addClass('open')
                .find('.o_mention_proposition').first().addClass('active');
            this.open = true;
        } else {
            this.$el.removeClass('open');
            this.$el.empty();
            this.open = false;
        }
    },
    _update_listener_selection: function (listener, selection) {
        listener.selection = selection;
        if (listener.notify_selection_changed) {
            this.trigger('selection_changed', listener);
        }
    },

    // Cursor position and selection utils
    _get_selection_positions: function () {
        var el = this.composer.$input.get(0);
        return el ? {start: el.selectionStart, end: el.selectionEnd} : {start: 0, end: 0};
    },
    _set_cursor_position: function (pos) {
        this.composer.$input.each(function (index, elem) {
            if (elem.setSelectionRange){
                elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
                elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
        });
    },

});

var Composer = Widget.extend({
    template: "mail.ChatComposer",

    events: {
        "keydown .o_composer_input": "on_keydown",
        "keyup .o_composer_input": "on_keyup",
        "change input.o_form_input_file": "on_attachment_change",
        "click .o_composer_button_send": "send_message",
        "click .o_composer_button_add_attachment": "on_click_add_attachment",
        "click .o_attachment_delete": "on_attachment_delete",
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            context: {},
            input_baseline: 18,
            input_max_height: 150,
            input_min_height: 28,
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
        this.mention_manager = new MentionManager(this);
        this.mention_manager.register({
            delimiter: '@',
            fetch_callback: this.mention_fetch_partners.bind(this),
            model: 'res.partner',
            notify_selection_changed: true,
            redirect_classname: 'o_mail_redirect',
            sort_selection: true,
            suggestions_template: 'mail.ChatComposer.MentionPartnerSuggestions',
        });
        this.mention_manager.register({
            delimiter: '#',
            fetch_callback: this.mention_fetch_channels.bind(this),
            model: 'mail.channel',
            redirect_classname: 'o_channel_redirect',
            suggestions_template: 'mail.ChatComposer.MentionChannelSuggestions'
        });
        this.mention_manager.on('selection_changed', this, this.mention_render_selection);
        this.PartnerModel = new Model('res.partner');
        this.ChannelModel = new Model('mail.channel');
    },

    start: function () {
        var self = this;

        this.$attachment_button = this.$(".o_composer_button_add_attachment");
        this.$attachments_list = this.$('.o_composer_attachments_list');
        this.$mention_partner_tags = this.$('.o_composer_mentioned_partners');
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
        this.mention_manager.prependTo(this.$('.o_composer'));

        return this._super();
    },

    preprocess_message: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer
        var value = this.$input.val().replace(/\n|\r/g, '<br/>');
        return $.when({
            content: this.mention_manager.generate_links(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.pluck(this.mention_manager.get_listener_selection('@'), 'id'),
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
            self.mention_manager.reset_selections();
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
                if (this.mention_manager.is_open()) {
                    event.preventDefault();
                }
                break;
            // BACKSPACE, DELETE: check if need to remove a mention
            case $.ui.keyCode.BACKSPACE:
            case $.ui.keyCode.DELETE:
                this.mention_manager.check_remove();
                break;
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if (this.mention_manager.is_open()) {
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
                this.mention_manager.proposition_navigation(event.which);
                break;
            // Otherwise, check if a mention is typed
            default:
                this.mention_manager.detect_delimiter();
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
    mention_fetch_channels: function (search) {
        var kwargs = {
            limit: this.options.mention_fetch_limit,
            search: search,
        };
        return this.ChannelModel
            .call('get_mention_suggestions', kwargs)
            .then(function (suggestions) {
                return _.partition(suggestions, function (suggestion) {
                    return _.contains(['public', 'groups'], suggestion.public);
                });
            });
    },
    mention_fetch_partners: function (search, listener) {
        var kwargs = {
            channel: this.get_channel_info(),
            exclude: listener ? _.pluck(listener.selection, 'id') : [],
            limit: this.options.mention_fetch_limit,
            search: search,
        };
        return this.PartnerModel.call('get_mention_suggestions', kwargs);
    },
    mention_render_selection: function (listener) {
        this.$mention_partner_tags.html(QWeb.render('mail.ChatComposer.MentionTags', {
            partners: listener.selection,
        }));
    },

    // Others
    is_empty: function () {
        return !this.$input.val().trim() && !this.$('.o_attachments').children().length;
    },
    focus: function () {
        this.$input.focus();
    },
});

return Composer;

});
