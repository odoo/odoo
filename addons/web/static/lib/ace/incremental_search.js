/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

define(function(require, exports, module) {
"use strict";

var oop = require("./lib/oop");
var Range = require("./range").Range;
var Search = require("./search").Search;
var SearchHighlight = require("./search_highlight").SearchHighlight;
var iSearchCommandModule = require("./commands/incremental_search_commands");
var ISearchKbd = iSearchCommandModule.IncrementalSearchKeyboardHandler;

/**
 * @class IncrementalSearch
 *
 * Implements immediate searching while the user is typing. When incremental
 * search is activated, keystrokes into the editor will be used for composing
 * a search term. Immediately after every keystroke the search is updated:
 * - so-far-matching characters are highlighted
 * - the cursor is moved to the next match
 *
 **/


/**
 *
 *
 * Creates a new `IncrementalSearch` object.
 *
 * @constructor
 **/
function IncrementalSearch() {
    this.$options = {wrap: false, skipCurrent: false};
    this.$keyboardHandler = new ISearchKbd(this);
}

oop.inherits(IncrementalSearch, Search);

// regexp handling

function isRegExp(obj) {
    return obj instanceof RegExp;
}

function regExpToObject(re) {
    var string = String(re),
        start = string.indexOf('/'),
        flagStart = string.lastIndexOf('/');
    return {
        expression: string.slice(start+1, flagStart),
        flags: string.slice(flagStart+1)
    }
}

function stringToRegExp(string, flags) {
    try {
        return new RegExp(string, flags);
    } catch (e) { return string; }
}

function objectToRegExp(obj) {
    return stringToRegExp(obj.expression, obj.flags);
}

// iSearch class

;(function() {

    this.activate = function(ed, backwards) {
        this.$editor = ed;
        this.$startPos = this.$currentPos = ed.getCursorPosition();
        this.$options.needle = '';
        this.$options.backwards = backwards;
        ed.keyBinding.addKeyboardHandler(this.$keyboardHandler);
        // we need to completely intercept paste, just registering an event handler does not work
        this.$originalEditorOnPaste = ed.onPaste; ed.onPaste = this.onPaste.bind(this);
        this.$mousedownHandler = ed.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.selectionFix(ed);
        this.statusMessage(true);
    };

    this.deactivate = function(reset) {
        this.cancelSearch(reset);
        var ed = this.$editor;
        ed.keyBinding.removeKeyboardHandler(this.$keyboardHandler);
        if (this.$mousedownHandler) {
            ed.removeEventListener('mousedown', this.$mousedownHandler);
            delete this.$mousedownHandler;
        }
        ed.onPaste = this.$originalEditorOnPaste;
        this.message('');
    };

    this.selectionFix = function(editor) {
        // Fix selection bug: When clicked inside the editor
        // editor.selection.$isEmpty is false even if the mouse click did not
        // open a selection. This is interpreted by the move commands to
        // extend the selection. To only extend the selection when there is
        // one, we clear it here
        if (editor.selection.isEmpty() && !editor.session.$emacsMark) {
            editor.clearSelection();
        }
    };

    this.highlight = function(regexp) {
        var sess = this.$editor.session,
            hl = sess.$isearchHighlight = sess.$isearchHighlight || sess.addDynamicMarker(
                new SearchHighlight(null, "ace_isearch-result", "text"));
        hl.setRegexp(regexp);
        sess._emit("changeBackMarker"); // force highlight layer redraw
    };

    this.cancelSearch = function(reset) {
        var e = this.$editor;
        this.$prevNeedle = this.$options.needle;
        this.$options.needle = '';
        if (reset) {
            e.moveCursorToPosition(this.$startPos);
            this.$currentPos = this.$startPos;
        } else {
            e.pushEmacsMark && e.pushEmacsMark(this.$startPos, false);
        }
        this.highlight(null);
        return Range.fromPoints(this.$currentPos, this.$currentPos);
    };

    this.highlightAndFindWithNeedle = function(moveToNext, needleUpdateFunc) {
        if (!this.$editor) return null;
        var options = this.$options;

        // get search term
        if (needleUpdateFunc) {
            options.needle = needleUpdateFunc.call(this, options.needle || '') || '';
        }
        if (options.needle.length === 0) {
            this.statusMessage(true);
            return this.cancelSearch(true);
        }

        // try to find the next occurence and enable  highlighting marker
        options.start = this.$currentPos;
        var session = this.$editor.session,
            found = this.find(session),
            shouldSelect = this.$editor.emacsMark ?
                !!this.$editor.emacsMark() : !this.$editor.selection.isEmpty();
        if (found) {
            if (options.backwards) found = Range.fromPoints(found.end, found.start);
            this.$editor.selection.setRange(Range.fromPoints(shouldSelect ? this.$startPos : found.end, found.end));
            if (moveToNext) this.$currentPos = found.end;
            // highlight after cursor move, so selection works properly
            this.highlight(options.re);
        }

        this.statusMessage(found);

        return found;
    };

    this.addString = function(s) {
        return this.highlightAndFindWithNeedle(false, function(needle) {
            if (!isRegExp(needle))
              return needle + s;
            var reObj = regExpToObject(needle);
            reObj.expression += s;
            return objectToRegExp(reObj);
        });
    };

    this.removeChar = function(c) {
        return this.highlightAndFindWithNeedle(false, function(needle) {
            if (!isRegExp(needle))
              return needle.substring(0, needle.length-1);
            var reObj = regExpToObject(needle);
            reObj.expression = reObj.expression.substring(0, reObj.expression.length-1);
            return objectToRegExp(reObj);
        });
    };

    this.next = function(options) {
        // try to find the next occurence of whatever we have searched for
        // earlier.
        // options = {[backwards: BOOL], [useCurrentOrPrevSearch: BOOL]}
        options = options || {};
        this.$options.backwards = !!options.backwards;
        this.$currentPos = this.$editor.getCursorPosition();
        return this.highlightAndFindWithNeedle(true, function(needle) {
            return options.useCurrentOrPrevSearch && needle.length === 0 ?
                this.$prevNeedle || '' : needle;
        });
    };

    this.onMouseDown = function(evt) {
        // when mouse interaction happens then we quit incremental search
        this.deactivate();
        return true;
    };

    this.onPaste = function(text) {
        this.addString(text);
    };

    this.convertNeedleToRegExp = function() {
        return this.highlightAndFindWithNeedle(false, function(needle) {
            return isRegExp(needle) ? needle : stringToRegExp(needle, 'ig');
        });
    };

    this.convertNeedleToString = function() {
        return this.highlightAndFindWithNeedle(false, function(needle) {
            return isRegExp(needle) ? regExpToObject(needle).expression : needle;
        });
    };

    this.statusMessage = function(found) {
        var options = this.$options, msg = '';
        msg += options.backwards ? 'reverse-' : '';
        msg += 'isearch: ' + options.needle;
        msg += found ? '' : ' (not found)';
        this.message(msg);
    };

    this.message = function(msg) {
        if (this.$editor.showCommandLine) {
            this.$editor.showCommandLine(msg);
            this.$editor.focus();
        } else {
            console.log(msg);
        }
    };

}).call(IncrementalSearch.prototype);


exports.IncrementalSearch = IncrementalSearch;


/**
 *
 * Config settings for enabling/disabling [[IncrementalSearch `IncrementalSearch`]].
 *
 **/

var dom = require('./lib/dom');
dom.importCssString && dom.importCssString("\
.ace_marker-layer .ace_isearch-result {\
  position: absolute;\
  z-index: 6;\
  -moz-box-sizing: border-box;\
  -webkit-box-sizing: border-box;\
  box-sizing: border-box;\
}\
div.ace_isearch-result {\
  border-radius: 4px;\
  background-color: rgba(255, 200, 0, 0.5);\
  box-shadow: 0 0 4px rgb(255, 200, 0);\
}\
.ace_dark div.ace_isearch-result {\
  background-color: rgb(100, 110, 160);\
  box-shadow: 0 0 4px rgb(80, 90, 140);\
}", "incremental-search-highlighting");

// support for default keyboard handler
var commands = require("./commands/command_manager");
(function() {
    this.setupIncrementalSearch = function(editor, val) {
        if (this.usesIncrementalSearch == val) return;
        this.usesIncrementalSearch = val;
        var iSearchCommands = iSearchCommandModule.iSearchStartCommands;
        var method = val ? 'addCommands' : 'removeCommands';
        this[method](iSearchCommands);
    };
}).call(commands.CommandManager.prototype);

// incremental search config option
var Editor = require("./editor").Editor;
require("./config").defineOptions(Editor.prototype, "editor", {
    useIncrementalSearch: {
        set: function(val) {
            this.keyBinding.$handlers.forEach(function(handler) {
                if (handler.setupIncrementalSearch) {
                    handler.setupIncrementalSearch(this, val);
                }
            });
            this._emit('incrementalSearchSettingChanged', {isEnabled: val});
        }
    }
});

});
