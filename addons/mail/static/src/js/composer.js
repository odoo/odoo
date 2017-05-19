odoo.define('mail.composer', function (require) {
"use strict";

var chat_mixin = require('mail.chat_mixin');
var DocumentViewer = require('mail.DocumentViewer');
var utils = require('mail.utils');

var config = require('web.config');
var core = require('web.core');
var data = require('web.data');
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
        "click .o_mention_proposition": "_onClickMentionItem",
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
            var inputMentions = this.composer.$input.text().match(new RegExp(delimiter+'[^ ]+(?= |&nbsp;)', 'g'));
            return this._validate_selection(listener.selection, inputMentions);
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
        var textVal = this.composer.$input.html();
        var cursorPosition = this._getSelectionPositions();
        var leftString = textVal.substring(0, cursorPosition);
        function validate_keyword (delimiter, beginning_only) {
            var delimiter_position = leftString.lastIndexOf(delimiter) - 1;
            if (beginning_only && delimiter_position > 0) {
                return false;
            }
            var search_str = textVal.substring(delimiter_position, cursorPosition);
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
     *
     * @private
     * @param {String} input_text: the text to search matches
     * @param {Object} listener: the listener for which we want to find a match
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    _get_match: function (input_text, listener) {
        // create the regex of all mention's names
        var names = _.pluck(listener.selection, 'name');
        var escaped_names = _.map(names, function (str) {
            return "("+_.str.escapeRegExp(listener.delimiter+str)+")(?= |&nbsp;)";
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
    /**
     * Get cursor position in contenteditable div with it's inner html content.
     *
     * @private
     * @return a current cursor position
    */
    _getSelectionPositions: function () {
        if (window.getSelection && window.getSelection().getRangeAt) {
            var range = window.getSelection().getRangeAt(0);
            var selectedObj = window.getSelection();
            var rangeCount = 0;
            var childNodes = selectedObj.anchorNode.parentNode.childNodes;
            for (var i = 0; i < childNodes.length; i++) {
                if (childNodes[i] === selectedObj.anchorNode) {
                    break;
                }
                if (childNodes[i].outerHTML)
                    rangeCount += childNodes[i].outerHTML.length;
                else if (childNodes[i].nodeType === 3) {
                    rangeCount += childNodes[i].textContent.length;
                }
            }
            return range.startOffset + rangeCount;
        }
        return -1;
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
    /*
     * Set cursor position after mention is added.
     * @private
     * @paran {int} node - id of childnode to set cursor position after it.
    */
    _setCursorPosition: function (nodeID) {
        var range = document.createRange();
        var selection = window.getSelection();
        range.setStart(document.getElementById(nodeID).nextSibling, 1);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
        this.composer.$input.focus();
    },
    _validate_selection: function (selection, inputMentions) {
        var validated_selection = [];
        _.each(inputMentions, function (mention) {
            var validated_mention = _.findWhere(selection, {name: mention.slice(1)});
            if (validated_mention) {
                validated_selection.push(validated_mention);
            }
        });
        return validated_selection;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * after click on mention item it set to a contenteditable div with it's new
     * cursor postion
     *
     * @private
     * @param {KeyboardEvent} event - to get a current selected mention from
     *   list and eventlistener.
     */
    _onClickMentionItem: function (event) {
        event.preventDefault();

        var textInput = this.composer.$input.html();
        var id = $(event.currentTarget).data('id');
        var selectedSuggestion = _.find(_.flatten(this.get('mention_suggestions')), function (s) {
            return s.id === id;
        });
        var substitution = selectedSuggestion.substitution;
        if (!substitution) { // no substitution string given, so use the mention name instead
            // replace white spaces with non-breaking spaces to facilitate mentions detection in text
            selectedSuggestion.name = selectedSuggestion.name.replace(/ /g, NON_BREAKING_SPACE);
            substitution = _.escape(this.active_listener.delimiter + selectedSuggestion.name);
        }
        var getMentionIndex = function (matches, cursorPosition) {
            for (var i=0; i<matches.length; i++) {
                if (cursorPosition <= matches[i].index) {
                    return i;
                }
            }
            return i;
        };

        // add the selected suggestion to the list
        if (this.active_listener.selection.length) {
            // get mention matches (ordered by index in the text)
            var matches = this._get_match(textInput, this.active_listener);
            var index = getMentionIndex(matches, this._getSelectionPositions());
            this.active_listener.selection.splice(index, 0, selectedSuggestion);
        } else {
            this.active_listener.selection.push(selectedSuggestion);
        }

        // update input text, and reset dropdown
        var cursorPosition = this._getSelectionPositions();
        var textLeft = textInput.substring(0, cursorPosition-(this.mention_word.length+1));
        var textRight = textInput.substring(cursorPosition, textInput.length);
        var nodeID = _.uniqueId('node');
        var newTextInput = textLeft + "<a id="+ nodeID+">" + substitution + "</a> " + textRight;
        this.composer.$input.html(newTextInput);
        this._setCursorPosition(nodeID);
        this.set('mention_suggestions', []);
    },

});

var BasicComposer = Widget.extend(chat_mixin, {
    template: "mail.ChatComposer",
    events: {
        "keydown .o_composer_input": "_onKeydown",
        "keyup .o_composer_input": "_onKeyup",
        "change input.o_input_file": "on_attachment_change",
        "click .o_composer_button_send": "send_message",
        "click .o_composer_button_add_attachment": "on_click_add_attachment",
        "click .o_attachment_delete": "on_attachment_delete",
        "click .o_attachment_download": "_onAttachmentDownload",
        "click .o_attachment_view": "_onAttachmentView",
        'click .o_composer_button_emoji': '_onEmojiButtonClick',
        'focusout .o_composer_button_emoji': '_onEmojiButtonFocusout',
        'focus .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageFocus',
        'click .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageClick',
        'input .o_composer_input': '_removeMention',
    },
    // RPCs done to fetch the mention suggestions are throttled with the following value
    MENTION_THROTTLE: 200,

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
            isMobile: config.device.isMobile
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

        this.isMini = options.isMini;

        this.avatarURL = session.uid > 0 ? session.url('/web/image', {
            model: 'res.users',
            field: 'image_small',
            id: session.uid,
        }) : '/web/static/src/img/user_menu_avatar.png';
    },

    start: function () {
        var self = this;

        this.$attachment_button = this.$(".o_composer_button_add_attachment");
        this.$attachments_list = this.$('.o_composer_attachments_list');
        this.$input = this.$('.o_composer_input');
        this.$input.focus(function () {
            self.trigger('input_focused');
        });
        this.$input.html(this.options.default_body);
        this.$input.css('min-height', this.options.input_min_height)

        // Attachments
        $(window).on(this.fileupload_id, this.on_attachment_loaded);
        this.on("change:attachment_ids", this, this.render_attachments);

        // Mention
        this.mention_manager.prependTo(this.$('.o_composer'));

        return this._super();
    },

    destroy: function () {
        $(window).off(this.fileupload_id);
        return this._super.apply(this, arguments);
    },

    preprocess_message: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer

        //Removing unwanted extra spaces from message
        var value = _.escape(this.$input.text()).trim();
        value = value.replace(/(\r|\n){2,}/g, '<br/><br/>');
        value = value.replace(/(\r|\n)/g, '<br/>');

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
        this.$input.html('');
        this.mention_manager.reset_selections();
        this.set('attachment_ids', []);
    },

    clear_composer_on_send: function() {
        this.clear_composer();
    },

    getState: function () {
        return {
            attachments: this.get('attachment_ids'),
            text: this.$input.html(),
        };
    },

    // Events
    on_click_add_attachment: function () {
        this.$('input.o_input_file').click();
        this.$input.focus();
    },

    setState: function (state) {
        this.set('attachment_ids', state.attachments);
        this.$input.html(state.text);
    },

    /**
     * Send the message on ENTER, but go to new line on SHIFT+ENTER
     */
    should_send: function (event) {
        return !event.shiftKey;
    },
    /**
     * _onKeydown event is triggered when is key is pressed
     *      - on UP and DOWN arrow is pressed then event prevents it's default
     *              behaviour if mention manager is open else it break it.
     *      - on ENTER key is pressed and mention manager is open then event
     *              prevents it's default behaviour else check if ControlKey is
     *              pressed or not if yes then it send a message
     *
     * @private
     * @param {KeyboardEvent} event
    */
    _onKeydown: function (event) {
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

    /**
     * _onKeyup event is triggered when key is released.
     * on ESCAP key it close the mention suggestion dropdown menu.
     * on ENTER key it selects that mention and add to a content editable div.
     * on UP or DOWN key it highlights previous or next mention respectively.
     *
     * @private
     * @param {KeyboardEvent} event
    */
    _onKeyup: function (event) {
        switch(event.which) {
            // ESCAPED KEYS: do nothing
            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_UP:
            case $.ui.keyCode.PAGE_DOWN:
                break;
            // ESCAPE: close mention propositions
            case $.ui.keyCode.ESCAPE:
                if (this.mention_manager.is_open()) {
                    event.stopPropagation();
                    this.mention_manager.reset_suggestions();
                } else {
                    this.trigger_up("escape_pressed");
                }
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
    // remove mention when user try to edit or remove it.
    _removeMention: function (event) {
        if (window.getSelection().anchorNode.parentNode.tagName == 'A') {
            document.getElementById(window.getSelection().anchorNode.parentNode.id).remove();
        }
    },

    // Mention
    mention_fetch_throttled: function (model, method, kwargs) {
        var self = this;
        // Delays the execution of the RPC to prevent unnecessary RPCs when the user is still typing
        var def = $.Deferred();
        clearTimeout(this.mention_fetch_timer);
        this.mention_fetch_timer = setTimeout(function () {
            return self._rpc({model: model, method: method, kwargs: kwargs})
                .then(function (results) {
                    def.resolve(results);
                });
        }, this.MENTION_THROTTLE);
        return def;
    },
    mention_fetch_channels: function (search) {
        return this.mention_fetch_throttled('mail.channel', 'get_mention_suggestions', {
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
                suggestions = self.mention_fetch_throttled('res.partner', 'get_mention_suggestions', {
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
            var canned_responses = self._getCannedResponses();
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
    /**
     * used to check if contenteditable div is empty or not
     *
     * @return - it returns length of attachment and trim content of input box
     * tp check for empty.
    */
    is_empty: function () {
        return !this.$input.text().trim() && !this.$('.o_attachments').children().length;
    },
    focus: function () {
        this.$input.focus();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Hides the emojis container.
     *
     * @private
     */
    _hideEmojis: function () {
        this.$emojisContainer.remove();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentDownload: function (event) {
        event.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentView: function (event) {
        var activeAttachmentID = $(event.currentTarget).data('id');
        var attachments = this.get('attachment_ids');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    /**
     * Called when the emoji button is clicked -> opens/hides the emoji panel.
     * Also, this method is in charge of the rendering of this panel the first
     * time it is opened.
     *
     * @private
     */
    _onEmojiButtonClick: function () {
        if (!this.$emojisContainer) { // lazy rendering
            this.$emojisContainer = $(QWeb.render('mail.ChatComposer.emojis', {
                emojis: this._getEmojis(),
            }));
        }
        if (this.$emojisContainer.parent().length) {
            this._hideEmojis();
        } else {
            this.$emojisContainer.appendTo(this.$('.o_composer_container'));
        }
    },
    /**
     * Called when the emoji button is blurred -> closes the emoji panel. The
     * closing is scheduled to be done at the end of the current execution
     * stack to allow stoping this closing if the button was focusout to select
     * an emoji (for example).
     *
     * @private
     */
    _onEmojiButtonFocusout: function () {
        this._hideEmojisTimeout = setTimeout(this._hideEmojis.bind(this), 0);
    },
    /**
     * Called when an emoji is focused -> @see _onEmojiButtonFocusout
     *
     * @private
     */
    _onEmojiImageFocus: function () {
        clearTimeout(this._hideEmojisTimeout);
    },
    /**
     * set cursor position at the end in input box
     *
     * @todo move that kind of code in a utility file. Maybe dom.js
     *
     * @private
     * @param {Element} el
     */
    _placeCaretAtEnd: function (el) {
        el.focus();
        if (typeof window.getSelection !== "undefined"
                && typeof document.createRange !== "undefined") {
            var range = document.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        } else if (typeof document.body.createTextRange !== "undefined") {
            var textRange = document.body.createTextRange();
            textRange.moveToElementText(el);
            textRange.collapse(false);
            textRange.select();
        }
    },
    /**
     * Called when an emoji is clicked -> adds it in the <input/>, focuses the
     * <input/> and closes the emoji panel.
     *
     * @private
     * @param {Event} ev
     */
    _onEmojiImageClick: function (ev) {
        this.$input.html(this.$input.html() + " " + $(ev.currentTarget).data('emoji') + " ");
        this._placeCaretAtEnd(this.$input[0])
        this._hideEmojis();
    },
});

var ExtendedComposer = BasicComposer.extend({
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            input_min_height: 120,
        });
        this._super(parent, options);
        this.extended = true;
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
    clear_composer: function () {
        this._super.apply(this, arguments);
        this.$subject_input.val('');
    },
    getState: function () {
        var state = this._super.apply(this, arguments);
        state.subject = this.$subject_input.val();
        return state;
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
    setState: function (state) {
        this._super.apply(this, arguments);
        this.set_subject(state.subject);
    },
});

return {
    BasicComposer: BasicComposer,
    ExtendedComposer: ExtendedComposer,
};

});
