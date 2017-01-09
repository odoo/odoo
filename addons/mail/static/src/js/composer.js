odoo.define('mail.composer', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var utils = require('mail.utils');

var core = require('web.core');
var data = require('web.data');
var dom_utils = require('web.dom_utils');
var Model = require('web.Model');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var NON_BREAKING_SPACE = '\u00a0';

var MENTION_PARTNER_DELIMITER = '@';
var MENTION_CHANNEL_DELIMITER = '#';
var MENTION_CANNED_RESPONSE_DELIMITER = ':';
var MENTION_COMMAND_DELIMITER = '/';

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
        var substitution = selected_suggestion.substitution;
        if (!substitution) { // no substitution string given, so use the mention name instead
            // replace white spaces with non-breaking spaces to facilitate mentions detection in text
            selected_suggestion.name = selected_suggestion.name.replace(/ /g, NON_BREAKING_SPACE);
            substitution = this.active_listener.delimiter + selected_suggestion.name;
        }
        var get_mention_index = function (matches, cursor_position) {
            for (var i=0; i<matches.length; i++) {
                if (cursor_position <= matches[i].index) {
                    return i;
                }
            }
            return i;
        };

        // add the selected suggestion to the list
        if (this.active_listener.selection.length) {
            // get mention matches (ordered by index in the text)
            var matches = this._get_match(text_input, this.active_listener);
            var index = get_mention_index(matches, this._get_selection_positions().start);
            this.active_listener.selection.splice(index, 0, selected_suggestion);
        } else {
            this.active_listener.selection.push(selected_suggestion);
        }

        // update input text, and reset dropdown
        var cursor_position = this._get_selection_positions().start;
        var text_left = text_input.substring(0, cursor_position-(this.mention_word.length+1));
        var text_right = text_input.substring(cursor_position, text_input.length);
        var text_input_new = text_left + substitution + ' ' + text_right;
        this.composer.$input.val(text_input_new);
        this._set_cursor_position(text_left.length+substitution.length+2);
        this.set('mention_suggestions', []);
        this.composer.focus(); // to trigger autoresize
    },

    // Public API
    /**
     * Registers a new listener, described by an object containing the following keys
     * @param {boolean} [beginning_only] true to enable autocomplete only at first position of input
     * @param {char} [delimiter] the mention delimiter
     * @param {function} [fetch_callback] the callback to fetch mention suggestions
     * @param {boolean} [generate_links] true to wrap mentions in <a> links
     * @param {string} [model] (optional) the model used for redirection
     * @param {string} [redirect_classname] (optional) the classname of the <a> wrapping the mention
     * @param {array} [selection] (optional) initial mentions for each listener
     * @param {string} [suggestion_template] the template of suggestions' dropdown
     */
    register: function (listener) {
        this.listeners.push(_.defaults(listener, {
            model: '',
            redirect_classname: '',
            selection: [],
        }));
    },

    /**
     * Returns true if the mention suggestions dropdown is open, false otherwise
     */
    is_open: function () {
        return this.open;
    },

    /**
     * Returns the mentions of the given listener that haven't been erased from the composer's input
     */
    get_listener_selection: function (delimiter) {
        var listener = _.findWhere(this.listeners, {delimiter: delimiter});
        if (listener) {
            var input_mentions = this.composer.$input.val().match(new RegExp(delimiter+'[^ ]+', 'g'));
            return this._validate_selection(listener.selection, input_mentions);
        }
        return [];
    },

    get_listener_selections: function () {
        var selections = {};
        _.each(this.listeners, function (listener) {
            selections[listener.delimiter] = listener.selection;
        });
        return selections;
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
        var text_val = this.composer.$input.val();
        var cursor_position = this._get_selection_positions().start;
        var left_string = text_val.substring(0, cursor_position);
        function validate_keyword (delimiter, beginning_only) {
            var delimiter_position = left_string.lastIndexOf(delimiter) - 1;
            if (beginning_only && delimiter_position > 0) {
                return false;
            }
            var search_str = text_val.substring(delimiter_position, cursor_position);
            var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
            var regex_start = new RegExp(pattern, "g");
            search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
            if (regex_start.test(search_str) && search_str.length > self.options.min_length) {
                search_str = search_str.replace(pattern, '');
                return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str.replace(delimiter, '') : false;
            }
            return false;
        }

        this.active_listener = undefined;
        for (var i=0; i<this.listeners.length; i++) {
            var listener = this.listeners[i];
            this.mention_word = validate_keyword(listener.delimiter, listener.beginning_only);

            if (this.mention_word !== false) {
                this.active_listener = listener;
                break;
            }
        }

        if (this.active_listener) {
            var mention_word = this.mention_word;
            $.when(this.active_listener.fetch_callback(mention_word)).then(function (suggestions) {
                if (mention_word === self.mention_word) {
                    // update suggestions only if mention_word didn't change in the meantime
                    self.set('mention_suggestions', suggestions);
                }
            });
        } else {
            this.set('mention_suggestions', []); // close the dropdown
        }
    },

    /**
     * Replaces mentions appearing in the string 's' by html links with proper redirection
     */
    generate_links: function (s) {
        var self = this;
        var base_href = session.url("/web");
        var mention_link = "<a href='%s' class='%s' data-oe-id='%s' data-oe-model='%s' target='_blank'>%s%s</a>";
        _.each(this.listeners, function (listener) {
            if (!listener.generate_links) {
                return;
            }
            var selection = listener.selection;
            if (selection.length) {
                var matches = self._get_match(s, listener);
                var substrings = [];
                var start_index = 0;
                for (var i=0; i<matches.length; i++) {
                    var match = matches[i];
                    var end_index = match.index + match[0].length;
                    var selection_id = self.get_selection_id(match, selection);
                    // put back white spaces instead of non-breaking spaces in mention's name
                    var match_name = match[0].substring(1).replace(new RegExp(NON_BREAKING_SPACE, 'g'), ' ');
                    var href = base_href + _.str.sprintf("#model=%s&id=%s", listener.model, selection_id);
                    var processed_text = _.str.sprintf(mention_link, href, listener.redirect_classname, selection_id, listener.model, listener.delimiter, match_name);
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

    get_selection_id: function (match, selection) {
        return _.findWhere(selection, {'name': match[0].slice(1)}).id;
    },

    reset_suggestions: function () {
        this.set('mention_suggestions', []);
    },
    reset_selections: function () {
        _.each(this.listeners, function (listener) {
            listener.selection = [];
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
        var suggestions = [];
        if (_.find(this.get('mention_suggestions'), _.isArray)) {
            // Array of arrays -> Flatten and insert dividers between groups
            var insert_divider = false;
            _.each(this.get('mention_suggestions'), function (suggestion_group) {
                if (suggestion_group.length > 0) {
                    if (insert_divider) {
                        suggestions.push({ divider: true });
                    }
                    suggestions = suggestions.concat(suggestion_group);
                    insert_divider = true;
                }
            });
        } else {
            suggestions = this.get('mention_suggestions');
        }
        if (suggestions.length) {
            this.$el.html(QWeb.render(this.active_listener.suggestion_template, {
                suggestions: suggestions,
            }));
            this.$el
                .addClass('open')
                .find('ul').css("max-width", this.composer.$input.width())
                .find('.o_mention_proposition').first().addClass('active');
            this.open = true;
        } else {
            this.$el.removeClass('open');
            this.$el.empty();
            this.open = false;
        }
    },
    _validate_selection: function (selection, input_mentions) {
        var validated_selection = [];
        _.each(input_mentions, function (mention) {
            var validated_mention = _.findWhere(selection, {name: mention.slice(1)});
            if (validated_mention) {
                validated_selection.push(validated_mention);
            }
        });
        return validated_selection;
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

var BasicComposer = Widget.extend({
    template: "mail.ChatComposer",

    events: {
        "keydown .o_composer_input textarea": "on_keydown",
        "keyup .o_composer_input": "on_keyup",
        "change input.o_form_input_file": "on_attachment_change",
        "click .o_composer_button_send": "send_message",
        "click .o_composer_button_add_attachment": "on_click_add_attachment",
        "click .o_attachment_delete": "on_attachment_delete",
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            commands_enabled: true,
            context: {},
            input_baseline: 18,
            input_max_height: 150,
            input_min_height: 28,
            mention_fetch_limit: 8,
            mention_partners_restricted: false, // set to true to only suggest prefetched partners
            send_text: _t('Send'),
            default_body: '',
            default_mention_selections: {},
        });
        this.context = this.options.context;

        // Attachments
        this.AttachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileupload_id = _.uniqueId('o_chat_fileupload');
        this.set('attachment_ids', []);

        // Mention
        this.mention_manager = new MentionManager(this);
        this.mention_manager.register({
            delimiter: MENTION_PARTNER_DELIMITER,
            fetch_callback: this.mention_fetch_partners.bind(this),
            generate_links: true,
            model: 'res.partner',
            redirect_classname: 'o_mail_redirect',
            selection: this.options.default_mention_selections[MENTION_PARTNER_DELIMITER],
            suggestion_template: 'mail.MentionPartnerSuggestions',
        });
        this.mention_manager.register({
            delimiter: MENTION_CHANNEL_DELIMITER,
            fetch_callback: this.mention_fetch_channels.bind(this),
            generate_links: true,
            model: 'mail.channel',
            redirect_classname: 'o_channel_redirect',
            selection: this.options.default_mention_selections[MENTION_CHANNEL_DELIMITER],
            suggestion_template: 'mail.MentionChannelSuggestions',
        });
        this.mention_manager.register({
            delimiter: MENTION_CANNED_RESPONSE_DELIMITER,
            fetch_callback: this.mention_get_canned_responses.bind(this),
            selection: this.options.default_mention_selections[MENTION_CANNED_RESPONSE_DELIMITER],
            suggestion_template: 'mail.MentionCannedResponseSuggestions',
        });
        if (this.options.commands_enabled) {
            this.mention_manager.register({
                beginning_only: true,
                delimiter: MENTION_COMMAND_DELIMITER,
                fetch_callback: this.mention_get_commands.bind(this),
                selection: this.options.default_mention_selections[MENTION_COMMAND_DELIMITER],
                suggestion_template: 'mail.MentionCommandSuggestions',
            });
        }

        // Emojis
        this.emoji_container_classname = 'o_composer_emoji';

        this.PartnerModel = new Model('res.partner');
        this.ChannelModel = new Model('mail.channel');
    },

    start: function () {
        var self = this;

        this.$attachment_button = this.$(".o_composer_button_add_attachment");
        this.$attachments_list = this.$('.o_composer_attachments_list');
        this.$input = this.$('.o_composer_input textarea');
        this.$input.focus(function () {
            self.trigger('input_focused');
        });
        this.$input.val(this.options.default_body);
        dom_utils.autoresize(this.$input, {parent: this, min_height: this.options.input_min_height});

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
            container: '.' + self.emoji_container_classname,
            trigger: 'focus',
        });

        // Mention
        this.mention_manager.prependTo(this.$('.o_composer'));

        return this._super();
    },

    destroy: function () {
        $(window).off(this.fileupload_id);
        return this._super.apply(this, arguments);
    },

    toggle: function(state) {
        this.$el.toggle(state);
    },

    preprocess_message: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer
        var value = _.escape(this.$input.val()).replace(/\n|\r/g, '<br/>');
        // prevent html space collapsing
        value = value.replace(/ /g, '&nbsp;').replace(/([^>])&nbsp;([^<])/g, '$1 $2');
        var commands = this.options.commands_enabled ? this.mention_manager.get_listener_selection('/') : [];
        return $.when({
            content: this.mention_manager.generate_links(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.uniq(_.pluck(this.mention_manager.get_listener_selection('@'), 'id')),
            command: commands.length > 0 ? commands[0].name : undefined,
        });
    },

    send_message: function () {
        if (this.is_empty() || !this.do_check_attachment_upload()) {
            return;
        }

        clearTimeout(this.canned_timeout);
        var self = this;
        this.preprocess_message().then(function (message) {
            self.trigger('post_message', message);
            self.clear_composer_on_send();
            self.$input.focus();
        });
    },

    clear_composer: function() {
        // Empty input, selected partners and attachments
        this.$input.val('');
        this.mention_manager.reset_selections();
        this.set('attachment_ids', []);
    },

    clear_composer_on_send: function() {
        this.clear_composer();
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
    should_send: function (event) {
        return !event.shiftKey;
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
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if (this.mention_manager.is_open()) {
                    event.preventDefault();
                } else {
                    var send_message = event.ctrlKey || this.should_send(event);
                    if (send_message) {
                        event.preventDefault();
                        this.send_message();
                    }
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
                event.stopPropagation();
                this.mention_manager.reset_suggestions();
                break;
            // ENTER, UP, DOWN: check if navigation in mention propositions
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                if (this.mention_manager.is_open()) {
                    this.mention_manager.proposition_navigation(event.which);
                }
                break;
            // Otherwise, check if a mention is typed
            default:
                this.mention_manager.detect_delimiter();
        }
    },

    // Attachments
    on_attachment_change: function(event) {
        var self = this,
            files = event.target.files,
            attachments = self.get('attachment_ids');

        _.each(files, function(file){
            var attachment = _.findWhere(attachments, {name: file.name});
            // if the files already exits, delete the file before upload
            if(attachment){
                self.AttachmentDataSet.unlink([attachment.id]);
                attachments = _.without(attachments, attachment);
            }
        });

        this.$('form.o_form_binary_form').submit();
        this.$attachment_button.prop('disabled', true);
        var upload_attachments = _.map(files, function(file){
            return {
                'id': 0,
                'name': file.name,
                'filename': file.name,
                'url': '',
                'upload': true,
                'mimetype': '',
            };
        });
        attachments = attachments.concat(upload_attachments);
        this.set('attachment_ids', attachments);
    },
    on_attachment_loaded: function(event) {
        var self = this,
            attachments = this.get('attachment_ids'),
            files = Array.prototype.slice.call(arguments, 1);

        _.each(files, function(file){
            if(file.error || !file.id){
                this.do_warn(file.error);
                attachments = _.filter(attachments, function (attachment) { return !attachment.upload; });
            }else{
                var attachment = _.findWhere(attachments, {filename: file.filename, upload: true});
                if(attachment){
                    attachments = _.without(attachments, attachment);
                    attachments.push({
                        'id': file.id,
                        'name': file.name || file.filename,
                        'filename': file.filename,
                        'mimetype': file.mimetype,
                        'url': session.url('/web/content', {'id': file.id, download: true}),
                    });
                }
            }
        }.bind(this));
        this.set('attachment_ids', attachments);
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
    mention_fetch_throttled: function (model, method, kwargs) {
        // Delays the execution of the RPC to prevent unnecessary RPCs when the user is still typing
        var def = $.Deferred();
        clearTimeout(this.mention_fetch_timer);
        this.mention_fetch_timer = setTimeout(function () {
            return model.call(method, kwargs).then(function (results) {
                def.resolve(results);
            });
        }, 200);
        return def;
    },
    mention_fetch_channels: function (search) {
        return this.mention_fetch_throttled(this.ChannelModel, 'get_mention_suggestions', {
            limit: this.options.mention_fetch_limit,
            search: search,
        }).then(function (suggestions) {
            return _.partition(suggestions, function (suggestion) {
                return _.contains(['public', 'groups'], suggestion.public);
            });
        });
    },
    mention_fetch_partners: function (search) {
        var self = this;
        return $.when(this.mention_prefetched_partners).then(function (prefetched_partners) {
            // filter prefetched partners with the given search string
            var suggestions = [];
            var limit = self.options.mention_fetch_limit;
            var search_regexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
            _.each(prefetched_partners, function (partners) {
                if (limit > 0) {
                    var filtered_partners = _.filter(partners, function (partner) {
                        return partner.email && search_regexp.test(partner.email) ||
                               partner.name && search_regexp.test(utils.unaccent(partner.name));
                    });
                    if (filtered_partners.length) {
                        suggestions.push(filtered_partners.slice(0, limit));
                        limit -= filtered_partners.length;
                    }
                }
            });
            if (!suggestions.length && !self.options.mention_partners_restricted) {
                // no result found among prefetched partners, fetch other suggestions
                suggestions = self.mention_fetch_throttled(self.PartnerModel, 'get_mention_suggestions', {
                    limit: limit,
                    search: search,
                });
            }
            return suggestions;
        });
    },
    mention_get_canned_responses: function (search) {
        var self = this;
        var def = $.Deferred();
        clearTimeout(this.canned_timeout);
        this.canned_timeout = setTimeout(function() {
            var canned_responses = chat_manager.get_canned_responses();
            var matches = fuzzy.filter(utils.unaccent(search), _.pluck(canned_responses, 'source'));
            var indexes = _.pluck(matches.slice(0, self.options.mention_fetch_limit), 'index');
            def.resolve(_.map(indexes, function (i) {
                return canned_responses[i];
            }));
        }, 500);
        return def;
    },
    mention_get_commands: function (search) {
        var search_regexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
        return _.filter(this.mention_commands, function (command) {
            return search_regexp.test(command.name);
        }).slice(0, this.options.mention_fetch_limit);
    },
    mention_set_prefetched_partners: function (prefetched_partners) {
        this.mention_prefetched_partners = prefetched_partners;
    },
    mention_set_enabled_commands: function (commands) {
        this.mention_commands = commands;
    },
    mention_get_listener_selections: function () {
        return this.mention_manager.get_listener_selections();
    },

    // Others
    is_empty: function () {
        return !this.$input.val().trim() && !this.$('.o_attachments').children().length;
    },
    focus: function () {
        this.$input.focus();
    },
});

var ExtendedComposer = BasicComposer.extend({
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            input_min_height: 120,
        });
        this._super(parent, options);
        this.extended = true;
        this.emoji_container_classname = 'o_extended_composer_emoji';
    },

    start: function () {
        this.$subject_input = this.$(".o_composer_subject input");
        return this._super.apply(this, arguments);
    },

    preprocess_message: function () {
        var self = this;
        return this._super().then(function (message) {
            var subject = self.$subject_input.val();
            self.$subject_input.val("");
            message.subject = subject;
            return message;
        });
    },

    should_send: function () {
        return false;
    },
    focus: function (target) {
        if (target === 'body') {
            this.$input.focus();
        } else {
            this.$subject_input.focus();
        }
    },
    set_subject: function(subject) {
        this.$('.o_composer_subject input').val(subject);
    },
});

return {
    BasicComposer: BasicComposer,
    ExtendedComposer: ExtendedComposer,
};

});
