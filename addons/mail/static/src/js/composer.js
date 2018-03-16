odoo.define('mail.composer', function (require) {
"use strict";

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
        'mouseover .o_mention_proposition': '_onHoverMentionProposition',
        'click .o_mention_proposition': '_onClickMentionItem',
    },
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this._composer = parent;
        this.options = _.extend({}, options, {
            minLength: 0,
        });

        this._open = false;
        this._listeners = [];
        this.set('mention_suggestions', []);
        this.on('change:mention_suggestions', this, this._renderSuggestions);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Registers a new listener, described by an object containing the following keys
     *
     * @param {boolean} [beginningOnly] true to enable autocomplete only at first position of input
     * @param {char} [delimiter] the mention delimiter
     * @param {function} [fetchCallback] the callback to fetch mention suggestions
     * @param {boolean} [generateLinks] true to wrap mentions in <a> links
     * @param {string} [model] (optional) the model used for redirection
     * @param {string} [redirectClassname] (optional) the classname of the <a> wrapping the mention
     * @param {array} [selection] (optional) initial mentions for each listener
     * @param {string} [suggestionTemplate] the template of suggestions' dropdown
     */
    register: function (listener) {
        this._listeners.push(_.defaults(listener, {
            model: '',
            redirectClassname: '',
            selection: [],
        }));
    },
    /**
     * Returns true if the mention suggestions dropdown is open, false otherwise
     *
     * @return {boolean}
     */
    isOpen: function () {
        return this._open;
    },
    /**
     * Returns the mentions of the given listener that haven't been erased from the composer's input
     *
     * @return {Array}
     */
    getListenerSelection: function (delimiter) {
        var listener = _.findWhere(this._listeners, {delimiter: delimiter});
        if (listener) {
            var inputMentions = this._composer.$input.text().match(new RegExp(delimiter+'[^ ]+(?= |&nbsp;)', 'g'));
            return this._validateSelection(listener.selection, inputMentions);
        }
        return [];
    },
    /**
     * @return {Array}
     */
    getListenerSelections: function () {
        var selections = {};
        _.each(this._listeners, function (listener) {
            selections[listener.delimiter] = listener.selection;
        });
        return selections;
    },
    /**
     * Detects if the user is currently typing a mention word
     *
     * @return the search string if it is, false otherwise
     */
    detectDelimiter: function () {
        var self = this;
        var textVal = this._composer.$input.html();
        var cursorPosition = this._getSelectionPositions();
        var leftString = textVal.substring(0, cursorPosition);

        function validateKeyword (delimiter, beginningOnly) {
            var delimiterPosition = leftString.lastIndexOf(delimiter) - 1;
            if (beginningOnly && delimiterPosition > 0) {
                return false;
            }
            var searchStr = textVal.substring(delimiterPosition, cursorPosition);
            var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
            var regexStart = new RegExp(pattern, 'g');
            searchStr = searchStr.replace(/^\s\s*|^[\n\r]/g, '');
            if (regexStart.test(searchStr) && searchStr.length > self.options.minLength) {
                searchStr = searchStr.replace(pattern, '');
                return searchStr.indexOf(' ') < 0 && !/[\r\n]/.test(searchStr) ? searchStr.replace(delimiter, '') : false;
            }
            return false;
        }

        this._activeListener = undefined;
        for (var i = 0; i < this._listeners.length; i++) {
            var listener = this._listeners[i];
            this._mentionWord = validateKeyword(listener.delimiter, listener.beginningOnly);

            if (this._mentionWord !== false) {
                this._activeListener = listener;
                break;
            }
        }

        if (this._activeListener) {
            var mentionWord = this._mentionWord;
            $.when(this._activeListener.fetchCallback(mentionWord)).then(function (suggestions) {
                if (mentionWord === self._mentionWord) {
                    // update suggestions only if mentionWord didn't change in the meantime
                    self.set('mention_suggestions', suggestions);
                }
            });
        } else {
            this.set('mention_suggestions', []); // close the dropdown
        }
    },
    /**
     * Replaces mentions appearing in the string 's' by html links with proper redirection
     *
     * @param {string} s
     * @return {string}
     */
    generateLinks: function (s) {
        var self = this;
        var baseHREF = session.url('/web');
        var mentionLink = "<a href='%s' class='%s' data-oe-id='%s' data-oe-model='%s' target='_blank'>%s%s</a>";
        _.each(this._listeners, function (listener) {
            if (!listener.generateLinks) {
                return;
            }
            var selection = listener.selection;
            if (selection.length) {
                var matches = self._getMatch(s, listener);
                var substrings = [];
                var startIndex = 0;
                for (var i = 0; i < matches.length; i++) {
                    var match = matches[i];
                    var endIndex = match.index + match[0].length;
                    var selectionID = self._getSelectionID(match, selection);
                    // put back white spaces instead of non-breaking spaces in mention's name
                    var matchName = match[0].substring(1).replace(new RegExp(NON_BREAKING_SPACE, 'g'), ' ');
                    var href = baseHREF + _.str.sprintf("#model=%s&id=%s", listener.model, selectionID);
                    var processedText = _.str.sprintf(mentionLink,
                                                      href,
                                                      listener.redirectClassname,
                                                      selectionID,
                                                      listener.model,
                                                      listener.delimiter,
                                                      matchName);
                    var subtext = s.substring(startIndex, endIndex).replace(match[0], processedText);
                    substrings.push(subtext);
                    startIndex = endIndex;
                }
                substrings.push(s.substring(startIndex, s.length));
                s = substrings.join('');
            }
        });
        return s;
    },
    resetSuggestions: function () {
        this.set('mention_suggestions', []);
    },
    resetSelections: function () {
        _.each(this._listeners, function (listener) {
            listener.selection = [];
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the matches (as RexExp.exec does) for the mention in the input text
     *
     * @private
     * @param {String} inputText: the text to search matches
     * @param {Object} listener: the listener for which we want to find a match
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    _getMatch: function (inputText, listener) {
        // create the regex of all mention's names
        var names = _.pluck(listener.selection, 'name');
        var escapedNames = _.map(names, function (str) {
            return "("+_.str.escapeRegExp(listener.delimiter+str)+")";
        });
        var regexStr = escapedNames.join('|');
        // extract matches
        var result = [];
        if (regexStr.length) {
            var myRegexp = new RegExp(regexStr, 'g');
            var match = myRegexp.exec(inputText);
            while (match !== null) {
                result.push(match);
                match = myRegexp.exec(inputText);
            }
        }
        return result;
    },
    /**
     * @private
     * @param {*} match
     * @param {*} selection
     * @return {*}
     */
    _getSelectionID: function (match, selection) {
        return _.findWhere(selection, { 'name': match[0].slice(1) }).id;
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
    /**
     * @private
     * @param {integer} keycode
     */
    _propositionNavigation: function (keycode) {
        var $active = this.$('.o_mention_proposition.active');
        if (keycode === $.ui.keyCode.ENTER) { // selecting proposition
            $active.click();
        } else { // navigation in propositions
            var $to;
            if (keycode === $.ui.keyCode.DOWN) {
                $to = $active.nextAll('.o_mention_proposition').first();
            } else if (keycode === $.ui.keyCode.UP) {
                $to = $active.prevAll('.o_mention_proposition').first();
            } else if (keycode === $.ui.keyCode.TAB) {
                $to = $active.nextAll('.o_mention_proposition').first();
                if (!$to.length) {
                    $to = $active.prevAll('.o_mention_proposition').last();
                }
            }
            if ($to && $to.length) {
                $active.removeClass('active');
                $to.addClass('active');
            }
        }
    },
    /**
     * @private
     */
    _renderSuggestions: function () {
        var suggestions = [];
        if (_.find(this.get('mention_suggestions'), _.isArray)) {
            // Array of arrays -> Flatten and insert dividers between groups
            var insertDivider = false;
            _.each(this.get('mention_suggestions'), function (suggestionGroup) {
                if (suggestionGroup.length > 0) {
                    if (insertDivider) {
                        suggestions.push({ divider: true });
                    }
                    suggestions = suggestions.concat(suggestionGroup);
                    insertDivider = true;
                }
            });
        } else {
            suggestions = this.get('mention_suggestions');
        }
        if (suggestions.length) {
            this.$el.html(QWeb.render(this._activeListener.suggestionTemplate, {
                suggestions: suggestions,
            }));
            this.$el
                .addClass('open')
                .find('ul').css('max-width', this._composer.$input.width())
                .find('.o_mention_proposition').first().addClass('active');
            this._open = true;
        } else {
            this.$el.removeClass('open');
            this.$el.empty();
            this._open = false;
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
        this._composer.$input.focus();
    },
    /**
     * @private
     * @param {*} selection
     * @param {Array} inputMentions
     * @return {Array}
     */
    _validateSelection: function (selection, inputMentions) {
        var validatedSelection = [];
        _.each(inputMentions, function (mention) {
            var validatedMention = _.findWhere(selection, { name: mention.slice(1) });
            if (validatedMention) {
                validatedSelection.push(validatedMention);
            }
        });
        return validatedSelection;
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

        var textInput = this._composer.$input.html();
        var id = $(event.currentTarget).data('id');
        var selectedSuggestion = _.find(_.flatten(this.get('mention_suggestions')), function (s) {
            return s.id === id;
        });
        var substitution = selectedSuggestion.substitution;
        if (!substitution) { // no substitution string given, so use the mention name instead
            // replace white spaces with non-breaking spaces to facilitate mentions detection in text
            selectedSuggestion.name = selectedSuggestion.name.replace(/ /g, NON_BREAKING_SPACE);
            substitution = _.escape(this._activeListener.delimiter + selectedSuggestion.name);
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
        if (this._activeListener.selection.length) {
            // get mention matches (ordered by index in the text)
            var matches = this._getMatch(textInput, this._activeListener);
            var index = getMentionIndex(matches, this._getSelectionPositions());
            this._activeListener.selection.splice(index, 0, selectedSuggestion);
        } else {
            this._activeListener.selection.push(selectedSuggestion);
        }

        // update input text, and reset dropdown
        var cursorPosition = this._getSelectionPositions();
        var textLeft = textInput.substring(0, cursorPosition-(this._mentionWord.length+1));
        var textRight = textInput.substring(cursorPosition, textInput.length);
        var nodeID = _.uniqueId('node');
        var newTextInput = textLeft + "<a id="+ nodeID+">" + substitution + "</a> " + textRight;
        this._composer.$input.html(newTextInput);
        this._setCursorPosition(nodeID);
        this.set('mention_suggestions', []);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onHoverMentionProposition: function (ev) {
        var $elem = $(ev.currentTarget);
        this.$('.o_mention_proposition').removeClass('active');
        $elem.addClass('active');
    },

});

var BasicComposer = Widget.extend({
    template: "mail.ChatComposer",
    events: {
        'keydown .o_composer_input': '_onKeydown',
        'keyup .o_composer_input': '_onKeyup',
        'change input.o_input_file': '_onAttachmentChange',
        'click .o_composer_button_send': '_sendMessage',
        'click .o_composer_button_add_attachment': '_onClickAddAttachment',
        'click .o_attachment_delete': '_onAttachmentDelete',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
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
            commandsEnabled: true,
            context: {},
            inputMinHeight: 28,
            mentionFetchLimit: 8,
            mentionPartnersRestricted: false, // set to true to only suggest prefetched partners
            sendText: _t("Send"),
            defaultBody: '',
            defaultMentionSelections: {},
            isMobile: config.device.isMobile
        });
        this.context = this.options.context;

        // Attachments
        this._attachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileuploadID = _.uniqueId('o_chat_fileupload');
        this.set('attachment_ids', []);

        // Mention
        this._mentionManager = new MentionManager(this);
        this._mentionManager.register({
            delimiter: MENTION_PARTNER_DELIMITER,
            fetchCallback: this._mentionFetchPartners.bind(this),
            generateLinks: true,
            model: 'res.partner',
            redirectClassname: 'o_mail_redirect',
            selection: this.options.defaultMentionSelections[MENTION_PARTNER_DELIMITER],
            suggestionTemplate: 'mail.MentionPartnerSuggestions',
        });
        this._mentionManager.register({
            delimiter: MENTION_CHANNEL_DELIMITER,
            fetchCallback: this._mentionFetchChannels.bind(this),
            generateLinks: true,
            model: 'mail.channel',
            redirectClassname: 'o_channel_redirect',
            selection: this.options.defaultMentionSelections[MENTION_CHANNEL_DELIMITER],
            suggestionTemplate: 'mail.MentionChannelSuggestions',
        });
        this._mentionManager.register({
            delimiter: MENTION_CANNED_RESPONSE_DELIMITER,
            fetchCallback: this._mentionGetCannedResponses.bind(this),
            selection: this.options.defaultMentionSelections[MENTION_CANNED_RESPONSE_DELIMITER],
            suggestionTemplate: 'mail.MentionCannedResponseSuggestions',
        });
        if (this.options.commandsEnabled) {
            this._mentionManager.register({
                beginningOnly: true,
                delimiter: MENTION_COMMAND_DELIMITER,
                fetchCallback: this._mentionGetCommands.bind(this),
                selection: this.options.defaultMentionSelections[MENTION_COMMAND_DELIMITER],
                suggestionTemplate: 'mail.MentionCommandSuggestions',
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

        this._$attachmentButton = this.$('.o_composer_button_add_attachment');
        this._$attachmentsList = this.$('.o_composer_attachments_list');
        this.$input = this.$('.o_composer_input');
        this.$input.focus(function () {
            self.trigger('input_focused');
        });
        this.$input.html(this.options.defaultBody);
        this.$input.css('min-height', this.options.inputMinHeight);

        // Attachments
        $(window).on(this.fileuploadID, this._onAttachmentLoaded);
        this.on('change:attachment_ids', this, this._renderAttachments);

        // Mention
        this._mentionManager.prependTo(this.$('.o_composer'));

        return this._super();
    },
    destroy: function () {
        $(window).off(this.fileuploadID);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Empty input, selected partners and attachments
     */
    clearComposer: function () {
        this.$input.html('');
        this._mentionManager.resetSelections();
        this.set('attachment_ids', []);
    },
    clearComposerOnSend: function () {
        this.clearComposer();
    },
    /**
     * Set the focus on the input
     */
    focus: function () {
        this.$input.focus();
    },
    /**
     * @private {Object}
     */
    getState: function () {
        return {
            attachments: this.get('attachment_ids'),
            text: this.$input.html(),
        };
    },
    /**
     * used to check if contenteditable div is empty or not
     *
     * @return {integer} it returns length of attachment and trim content of input box
     * tp check for empty.
    */
    isEmpty: function () {
        return !this.$input.text().trim() && !this.$('.o_attachments').children().length;
    },
    /**
     * @param {Object} state
     * @param {Array} state.attachments
     * @param {string} state.text
     */
    setState: function (state) {
        this.set('attachment_ids', state.attachments);
        this.$input.html(state.text);
    },
    /**
     * @param {$.Deferred<Object[]>} prefetchedPartners
     */
    mentionSetPrefetchedPartners: function (prefetchedPartners) {
        this._mentionPrefetchedPartners = prefetchedPartners;
    },
    /**
     * @param {*} commands
     */
    mentionSetEnabledCommands: function (commands) {
        this._mentionCommands = commands;
    },
    /**
     * @return {*}
     */
    mentionGetListenerSelections: function () {
        return this._mentionManager.getListenerSelections();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _doCheckAttachmentUpload: function () {
        if (_.find(this.get('attachment_ids'), function (file) { return file.upload; })) {
            this.do_warn(_t("Uploading error"), _t("Please, wait while the file is uploading."));
            return false;
        }
        return true;
    },
    /**
     * Hides the emojis container.
     *
     * @private
     */
    _hideEmojis: function () {
        this._$emojisContainer.remove();
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionGetCannedResponses: function (search) {
        var self = this;
        var def = $.Deferred();
        clearTimeout(this.canned_timeout);
        this.canned_timeout = setTimeout(function () {
            var cannedResponses = self.call('chat_service', 'getCannedResponses');
            var matches = fuzzy.filter(utils.unaccent(search), _.pluck(cannedResponses, 'source'));
            var indexes = _.pluck(matches.slice(0, self.options.mentionFetchLimit), 'index');
            def.resolve(_.map(indexes, function (index) {
                return cannedResponses[index];
            }));
        }, 500);
        return def;
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionGetCommands: function (search) {
        var search_regexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
        return _.filter(this._mentionCommands, function (command) {
            return search_regexp.test(command.name);
        }).slice(0, this.options.mentionFetchLimit);
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionFetchChannels: function (search) {
        return this._mentionFetchThrottled('mail.channel', 'get_mention_suggestions', {
            limit: this.options.mentionFetchLimit,
            search: search,
        }).then(function (suggestions) {
            return _.partition(suggestions, function (suggestion) {
                return _.contains(['public', 'groups'], suggestion.public);
            });
        });
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionFetchPartners: function (search) {
        var self = this;
        return $.when(this._mentionPrefetchedPartners).then(function (partners) {
            // filter prefetched partners with the given search string
            var suggestions = [];
            var limit = self.options.mentionFetchLimit;
            var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
            if (limit > 0) {
                var filteredPartners = _.filter(partners, function (partner) {
                    return partner.email && searchRegexp.test(partner.email) ||
                           partner.name && searchRegexp.test(utils.unaccent(partner.name));
                });
                if (filteredPartners.length) {
                    suggestions.push(filteredPartners.slice(0, limit));
                    limit -= filteredPartners.length;
                }
            }
            if (!suggestions.length && !self.options.mentionPartnersRestricted) {
                // no result found among prefetched partners, fetch other suggestions
                suggestions = self._mentionFetchThrottled('res.partner', 'get_mention_suggestions', {
                    limit: limit,
                    search: search,
                });
            }
            return suggestions;
        });
    },
    /**
     * @private
     * @param {string} model
     * @param {string} method
     * @param {Object} kwargs
     * @return {$.Deferred}
     */
    _mentionFetchThrottled: function (model, method, kwargs) {
        var self = this;
        // Delays the execution of the RPC to prevent unnecessary RPCs when the user is still typing
        var def = $.Deferred();
        clearTimeout(this.mentionFetchTimer);
        this.mentionFetchTimer = setTimeout(function () {
            return self._rpc({model: model, method: method, kwargs: kwargs})
                .then(function (results) {
                    def.resolve(results);
                });
        }, this.MENTION_THROTTLE);
        return def;
    },
    /**
     * Set cursor position at the end in input box
     *
     * @todo move that kind of code in a utility file. Maybe dom.js
     *
     * @private
     * @param {Element} el
     */
    _placeCaretAtEnd: function (el) {
        el.focus();
        if (
            typeof window.getSelection !== 'undefined' &&
            typeof document.createRange !== 'undefined'
        ) {
            var range = document.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        } else if (typeof document.body.createTextRange !== 'undefined') {
            var textRange = document.body.createTextRange();
            textRange.moveToElementText(el);
            textRange.collapse(false);
            textRange.select();
        }
    },
    /**
     * @private
     */
    _preprocessMessage: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer

        //Removing unwanted extra spaces from message
        var value = _.escape(this.$input.text()).trim();
        value = value.replace(/(\r|\n){2,}/g, '<br/><br/>');
        value = value.replace(/(\r|\n)/g, '<br/>');

        // prevent html space collapsing
        value = value.replace(/ /g, '&nbsp;').replace(/([^>])&nbsp;([^<])/g, '$1 $2');
        var commands = this.options.commandsEnabled ? this._mentionManager.getListenerSelection('/') : [];
        return $.when({
            content: this._mentionManager.generateLinks(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelection('@'), 'id')),
            command: commands.length > 0 ? commands[0].name : undefined,
        });
    },
    /**
     * Remove mention when user try to edit or remove it.
     *
     * @private
     */
    _removeMention: function () {
        if (window.getSelection().anchorNode.parentNode.tagName === 'A') {
            document.getElementById(window.getSelection().anchorNode.parentNode.id).remove();
        }
    },
    /**
     * @Private
     */
    _renderAttachments: function() {
        this._$attachmentsList.html(QWeb.render('mail.ChatComposer.Attachments', {
            attachments: this.get('attachment_ids'),
        }));
    },
    /**
     * @private
     */
    _sendMessage: function () {
        if (this.isEmpty() || !this._doCheckAttachmentUpload()) {
            return;
        }

        clearTimeout(this.canned_timeout);
        var self = this;
        this._preprocessMessage().then(function (message) {
            self.trigger('post_message', message);
            self.clearComposerOnSend();
            self.$input.focus();
        });
    },
    /**
     * Send the message on ENTER, but go to new line on SHIFT+ENTER
     *
     * @private
     */
    _shouldSend: function (ev) {
        return !ev.shiftKey;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery.Event} ev
     */
    _onAttachmentChange: function(ev) {
        var self = this,
            files = ev.target.files,
            attachments = self.get('attachment_ids');

        _.each(files, function(file){
            var attachment = _.findWhere(attachments, {name: file.name});
            // if the files already exits, delete the file before upload
            if (attachment){
                self._attachmentDataSet.unlink([attachment.id]);
                attachments = _.without(attachments, attachment);
            }
        });

        this.$('form.o_form_binary_form').submit();
        this._$attachmentButton.prop('disabled', true);
        var uploadAttachments = _.map(files, function(file){
            return {
                'id': 0,
                'name': file.name,
                'filename': file.name,
                'url': '',
                'upload': true,
                'mimetype': '',
            };
        });
        attachments = attachments.concat(uploadAttachments);
        this.set('attachment_ids', attachments);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentDelete: function(ev){
        ev.stopPropagation();
        var self = this;
        var attachmentID = $(ev.target).data('id');
        if (attachmentID) {
            var attachments = [];
            _.each(this.get('attachment_ids'), function(attachment){
                if (attachmentID !== attachment.id) {
                    attachments.push(attachment);
                } else {
                    self._attachmentDataSet.unlink([attachmentID]);
                }
            });
            this.set('attachment_ids', attachments);
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentDownload: function (ev) {
        ev.stopPropagation();
    },
    /**
     * @private
     */
    _onAttachmentLoaded: function () {
        var attachments = this.get('attachment_ids');
        var files = Array.prototype.slice.call(arguments, 1);

        _.each(files, function (file) {
            if (file.error || !file.id){
                this.do_warn(file.error);
                attachments = _.filter(attachments, function (attachment) { return !attachment.upload; });
            } else {
                var attachment = _.findWhere(attachments, {filename: file.filename, upload: true});
                if (attachment) {
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
        this._$attachmentButton.prop('disabled', false);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentView: function (ev) {
        var activeAttachmentID = $(ev.currentTarget).data('id');
        var attachments = this.get('attachment_ids');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    _onClickAddAttachment: function () {
        this.$('input.o_input_file').click();
        this.$input.focus();
    },
    /**
     * Called when the emoji button is clicked -> opens/hides the emoji panel.
     * Also, this method is in charge of the rendering of this panel the first
     * time it is opened.
     *
     * @private
     */
    _onEmojiButtonClick: function () {
        if (!this._$emojisContainer) { // lazy rendering
            this._$emojisContainer = $(QWeb.render('mail.ChatComposer.emojis', {
                emojis: this.call('chat_service', 'getEmojis'),
            }));
        }
        if (this._$emojisContainer.parent().length) {
            this._hideEmojis();
        } else {
            this._$emojisContainer.appendTo(this.$('.o_composer_container'));
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
        if (this._$emojisContainer) {
            this._hideEmojisTimeout = setTimeout(this._hideEmojis.bind(this), 0);
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
        this._placeCaretAtEnd(this.$input[0]);
        this._hideEmojis();
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
     * _onKeydown event is triggered when is key is pressed
     *      - on UP and DOWN arrow is pressed then event prevents it's default
     *              behaviour if mention manager is open else it break it.
     *      - on ENTER key is pressed and mention manager is open then event
     *              prevents it's default behaviour else check if ControlKey is
     *              pressed or not if yes then it send a message
     *
     * @private
     * @param {KeyboardEvent} ev
    */
    _onKeydown: function (ev) {
        switch (ev.which) {
            // UP, DOWN, TAB: prevent moving cursor if navigation in mention propositions
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.TAB:
                if (this._mentionManager.isOpen()) {
                    ev.preventDefault();
                }
                break;
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if (this._mentionManager.isOpen()) {
                    ev.preventDefault();
                } else {
                    var sendMessage = ev.ctrlKey || this._shouldSend(ev);
                    if (sendMessage) {
                        ev.preventDefault();
                        this._sendMessage();
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
     * @param {KeyboardEvent} ev
    */
    _onKeyup: function (ev) {
        switch (ev.which) {
            // ESCAPED KEYS: do nothing
            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_UP:
            case $.ui.keyCode.PAGE_DOWN:
                break;
            // ESCAPE: close mention propositions
            case $.ui.keyCode.ESCAPE:
                if (this._mentionManager.isOpen()) {
                    ev.stopPropagation();
                    this._mentionManager.resetSuggestions();
                } else {
                    this.trigger_up('escape_pressed');
                }
                break;
            // ENTER, UP, DOWN, TAB: check if navigation in mention propositions
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.TAB:
                if (this._mentionManager.isOpen()) {
                    this._mentionManager._propositionNavigation(ev.which);
                }
                break;
            // Otherwise, check if a mention is typed
            default:
                this._mentionManager.detectDelimiter();
        }
    },
});

var ExtendedComposer = BasicComposer.extend({
    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            inputMinHeight: 120,
        });
        this._super(parent, options);
        this.extended = true;
    },
    /**
     * @override
     */
    start: function () {
        this._$subjectInput = this.$('.o_composer_subject input');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    clearComposer: function () {
        this._super.apply(this, arguments);
        this._$subjectInput.val('');
    },
    /**
     * @override
     * @param {*} target
     */
    focus: function (target) {
        if (target === 'body') {
            this.$input.focus();
        } else {
            this._$subjectInput.focus();
        }
    },
    /**
     * @override
     */
    getState: function () {
        var state = this._super.apply(this, arguments);
        state.subject = this._$subjectInput.val();
        return state;
    },
    /**
     * @override
     * @param {Object} state
     * @param {string} state.subject
     */
    setState: function (state) {
        this._super.apply(this, arguments);
        this.setSubject(state.subject);
    },
    /**
     * @param {string} subject
     */
    setSubject: function(subject) {
        this.$('.o_composer_subject input').val(subject);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _preprocessMessage: function () {
        var self = this;
        return this._super().then(function (message) {
            var subject = self._$subjectInput.val();
            self._$subjectInput.val("");
            message.subject = subject;
            return message;
        });
    },
    /**
     * @override
     * @private
     */
    _shouldSend: function () {
        return false;
    },
});

return {
    BasicComposer: BasicComposer,
    ExtendedComposer: ExtendedComposer,
};

});
