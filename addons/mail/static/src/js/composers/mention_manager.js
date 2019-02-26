odoo.define('mail.composer.MentionManager', function (require) {
"use strict";

var core = require('web.core');
var dom = require('web.dom');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var NON_BREAKING_SPACE = '\u00a0';

// The MentionManager allows the Composer to register listeners. For each
// listener, it detects if the user is currently typing a mention (starting by a
// given delimiter). If so, if fetches mention suggestions and renders them. On
// suggestion clicked, it updates the selection for the corresponding listener.
var MentionManager = Widget.extend({
    className: 'dropup o_composer_mention_dropdown',
    events: {
        'click .o_mention_proposition': '_onClickMentionItem',
        'mouseover .o_mention_proposition': '_onHoverMentionProposition',
    },
    init: function (parent) {
        this._super.apply(this, arguments);

        this._composer = parent;

        this._open = false;
        this._listeners = [];
        this.set('mention_suggestions', []);
        this.on('change:mention_suggestions', this, this._renderSuggestions);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns true if the mention suggestions dropdown is open, false otherwise
     *
     * @returns {boolean}
     */
    isOpen: function () {
        return this._open;
    },
    /**
     * Returns the mentions of the given listener that haven't been erased from
     * the composer's input
     *
     * @returns {Array}
     */
    getListenerSelection: function (delimiter) {
        var listener = _.findWhere(this._listeners, { delimiter: delimiter });
        if (listener) {
            var escapedVal = _.escape(this._composer.$input.val());
            var inputMentions = escapedVal.match(new RegExp(delimiter+'[^ ]+(?= |&nbsp;|$)', 'g'));
            return this._validateSelection(listener.selection, inputMentions);
        }
        return [];
    },
    /**
     * @returns {Object} containing listener selections, grouped by delimiter
     *   as key of the object.
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
     */
    detectDelimiter: function () {
        var self = this;
        var textVal = this._composer.$input.val();
        var cursorPosition = this._getSelectionPositions().start;
        var leftString = textVal.substring(0, cursorPosition);

        function validateKeyword(delimiter, beginningOnly) {
            // use position before delimiter because there should be whitespaces
            // or line feed/carriage return before the delimiter
            var beforeDelimiterPosition = leftString.lastIndexOf(delimiter) - 1;
            if (beginningOnly && beforeDelimiterPosition > 0) {
                return false;
            }
            var searchStr = textVal.substring(beforeDelimiterPosition, cursorPosition);
            // regex string start with delimiter or whitespace then delimiter
            var pattern = "^"+delimiter+"|^\\s"+delimiter;
            var regexStart = new RegExp(pattern, 'g');
            // trim any left whitespaces or the left line feed/ carriage return
            // at the beginning of the string
            searchStr = searchStr.replace(/^\s\s*|^[\n\r]/g, '');
            if (regexStart.test(searchStr) && searchStr.length) {
                searchStr = searchStr.replace(pattern, '');
                return searchStr.indexOf(' ') < 0 && !/[\r\n]/.test(searchStr) ?
                        searchStr.replace(delimiter, '') :
                        false;
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
            $.when(this._activeListener.fetchCallback(mentionWord))
                .then(function (suggestions) {
                    if (mentionWord === self._mentionWord) {
                        // update suggestions only if mentionWord didn't change
                        // in the meantime
                        self.set('mention_suggestions', suggestions);
                    }
                });
        } else {
            this.set('mention_suggestions', []); // close the dropdown
        }
    },
    /**
     * Replaces mentions appearing in the string 's' by html links with proper
     * redirection
     *
     * @param {string} s
     * @returns {string}
     */
    generateLinks: function (s) {
        var self = this;
        var baseHREF = session.url('/web');
        var linkParams = "href='%s' class='%s' data-oe-id='%s' data-oe-model='%s' target='_blank'";
        var mentionLink = "<a " + linkParams + " >" +
                                "%s%s" +
                            "</a>";
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
                    // put back white spaces instead of non-breaking spaces in
                    // mention's name
                    var matchName = match[0].substring(1)
                                            .replace(new RegExp(NON_BREAKING_SPACE, 'g'), ' ');
                    var href = baseHREF +
                                _.str.sprintf("#model=%s&id=%s", listener.model, selectionID);
                    var processedText = _.str.sprintf(mentionLink,
                                                      href,
                                                      listener.redirectClassname,
                                                      selectionID,
                                                      listener.model,
                                                      listener.delimiter,
                                                      matchName);
                    substrings.push(s.substring(startIndex, match.index));
                    substrings.push(processedText);
                    startIndex = endIndex;
                }
                substrings.push(s.substring(startIndex, s.length));
                s = substrings.join('');
            }
        });
        return s;
    },
    /**
     * @param {integer} keycode
     */
    propositionNavigation: function (keycode) {
        var $active = this.$('.o_mention_proposition.active');
        if (keycode === $.ui.keyCode.ENTER) {
            // selecting proposition
            $active.click();
        } else {
            // navigation in propositions
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
     * Registers a new listener, described by an object containing the following
     * keys
     *
     * @param {Object} listener
     * @param {boolean} [listener.beginningOnly] true to enable autocomplete
     *   only at first position of input
     * @param {char} [listener.delimiter] the mention delimiter
     * @param {function} [listener.fetchCallback] the callback to fetch mention
     *   suggestions
     * @param {boolean} [listener.generateLinks] true to wrap mentions in <a>
     *   links
     * @param {string} [listener.model=''] (optional) the model used for
     *   redirection
     * @param {string} [listener.redirectClassname=''] (optional) the classname
     *   of the <a> wrapping the mention
     * @param {Array} [listener.selection=[]] (optional) initial mentions for
     *   each listener
     * @param {string} [listener.suggestionTemplate] the template of
     *   suggestions' dropdown
     */
    register: function (listener) {
        this._listeners.push(_.defaults(listener, {
            model: '',
            redirectClassname: '',
            selection: [],
        }));
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
     * Returns the matches (as RexExp.exec does) for the mention in the input
     * text
     *
     * @private
     * @param {string} inputText: the text to search matches
     * @param {Object} listener: the listener for which we want to find a match
     * @returns {Object[]} matches in the same format as RexExp.exec()
     */
    _getMatch: function (inputText, listener) {
        // create the regex of all mention's names
        var names = _.pluck(listener.selection, 'name');
        var escapedNames = _.map(names, function (str) {
            return "("+_.str.escapeRegExp(listener.delimiter+str)+")(?= |&nbsp;|$)";
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
     * @param {string[]} match
     * @param {Object} selection
     * @returns {Object}
     */
    _getSelectionID: function (match, selection) {
        return _.findWhere(selection, { name: match[0].slice(1) }).id;
    },
    /**
     * Get cursor position and selection
     *
     * @private
     * @returns a current cursor position
    */
    _getSelectionPositions: function () {
        var InputElement = this._composer.$input.get(0);
        return InputElement ? dom.getSelectionRange(InputElement) : { start: 0, end: 0 };
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
                .addClass('show')
                .find('.dropdown-menu')
                .addClass('show')
                .css('max-width', this._composer.$input.width())
                .find('.o_mention_proposition')
                .first()
                .addClass('active');
            this._open = true;
        } else {
            this.$el.removeClass('show')
                .find('.dropdown-menu')
                .removeClass('show');
            this.$el.empty();
            this._open = false;
        }
    },
    /*
     * Set cursor position
     *
     * @private
     * @param {integer} pos
    */
    _setCursorPosition: function (pos) {
        this._composer.$input.each(function (index, elem) {
            dom.setSelectionRange(elem, { start: pos, end: pos });
        });
    },
    /**
     * @private
     * @param {Object} selection
     * @param {Array} inputMentions
     * @returns {Array}
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
     * @private
     * @param {KeyboardEvent} ev - to get a current selected mention from list
     *   and eventlistener.
     */
    _onClickMentionItem: function (ev) {
        ev.preventDefault();

        var textInput = this._composer.$input.val();
        var id = $(ev.currentTarget).data('id');
        var suggestions = _.flatten(this.get('mention_suggestions'));
        var selectedSuggestion = _.clone(_.find(suggestions, function (s) {
            return s.id === id;
        }));
        var substitution = selectedSuggestion.substitution;
        if (!substitution) {
            // no substitution string given, so use the mention name instead
            // replace white spaces with non-breaking spaces to facilitate
            // mentions detection in text
            selectedSuggestion.name = selectedSuggestion.name.replace(/ /g, NON_BREAKING_SPACE);
            substitution = this._activeListener.delimiter + selectedSuggestion.name;
        }
        var getMentionIndex = function (matches, cursorPosition) {
            for (var i = 0; i < matches.length; i++) {
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
            var index = getMentionIndex(matches, this._getSelectionPositions().start);
            this._activeListener.selection.splice(index, 0, selectedSuggestion);
        } else {
            this._activeListener.selection.push(selectedSuggestion);
        }

        // update input text, and reset dropdown
        var cursorPosition = this._getSelectionPositions().start;
        var textLeft = textInput.substring(0, cursorPosition-(this._mentionWord.length+1));
        var textRight = textInput.substring(cursorPosition, textInput.length);
        var textInputNew = textLeft + substitution + ' ' + textRight;
        this._composer.$input.val(textInputNew);
        this._setCursorPosition(textLeft.length+substitution.length+2);
        this.set('mention_suggestions', []);
        this._composer.focus('body'); // to trigger autoresize
        // suggestion after inserting will be used with escaped content
        if (selectedSuggestion.name) {
            selectedSuggestion.name = _.escape(selectedSuggestion.name);
        }
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

return MentionManager;

});
