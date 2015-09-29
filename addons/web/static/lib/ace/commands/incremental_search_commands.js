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

var config = require("../config");
var oop = require("../lib/oop");
var HashHandler = require("../keyboard/hash_handler").HashHandler;
var occurStartCommand = require("./occur_commands").occurStartCommand;

// These commands can be installed in a normal key handler to start iSearch:
exports.iSearchStartCommands = [{
    name: "iSearch",
    bindKey: {win: "Ctrl-F", mac: "Command-F"},
    exec: function(editor, options) {
        config.loadModule(["core", "ace/incremental_search"], function(e) {
            var iSearch = e.iSearch = e.iSearch || new e.IncrementalSearch();
            iSearch.activate(editor, options.backwards);
            if (options.jumpToFirstMatch) iSearch.next(options);
        });
    },
    readOnly: true
}, {
    name: "iSearchBackwards",
    exec: function(editor, jumpToNext) { editor.execCommand('iSearch', {backwards: true}); },
    readOnly: true
}, {
    name: "iSearchAndGo",
    bindKey: {win: "Ctrl-K", mac: "Command-G"},
    exec: function(editor, jumpToNext) { editor.execCommand('iSearch', {jumpToFirstMatch: true, useCurrentOrPrevSearch: true}); },
    readOnly: true
}, {
    name: "iSearchBackwardsAndGo",
    bindKey: {win: "Ctrl-Shift-K", mac: "Command-Shift-G"},
    exec: function(editor) { editor.execCommand('iSearch', {jumpToFirstMatch: true, backwards: true, useCurrentOrPrevSearch: true}); },
    readOnly: true
}];

// These commands are only available when incremental search mode is active:
exports.iSearchCommands = [{
    name: "restartSearch",
    bindKey: {win: "Ctrl-F", mac: "Command-F"},
    exec: function(iSearch) {
        iSearch.cancelSearch(true);
    }
}, {
    name: "searchForward",
    bindKey: {win: "Ctrl-S|Ctrl-K", mac: "Ctrl-S|Command-G"},
    exec: function(iSearch, options) {
        options.useCurrentOrPrevSearch = true;
        iSearch.next(options);
    }
}, {
    name: "searchBackward",
    bindKey: {win: "Ctrl-R|Ctrl-Shift-K", mac: "Ctrl-R|Command-Shift-G"},
    exec: function(iSearch, options) {
        options.useCurrentOrPrevSearch = true;
        options.backwards = true;
        iSearch.next(options);
    }
}, {
    name: "extendSearchTerm",
    exec: function(iSearch, string) {
        iSearch.addString(string);
    }
}, {
    name: "extendSearchTermSpace",
    bindKey: "space",
    exec: function(iSearch) { iSearch.addString(' '); }
}, {
    name: "shrinkSearchTerm",
    bindKey: "backspace",
    exec: function(iSearch) {
        iSearch.removeChar();
    }
}, {
    name: 'confirmSearch',
    bindKey: 'return',
    exec: function(iSearch) { iSearch.deactivate(); }
}, {
    name: 'cancelSearch',
    bindKey: 'esc|Ctrl-G',
    exec: function(iSearch) { iSearch.deactivate(true); }
}, {
    name: 'occurisearch',
    bindKey: 'Ctrl-O',
    exec: function(iSearch) {
        var options = oop.mixin({}, iSearch.$options);
        iSearch.deactivate();
        occurStartCommand.exec(iSearch.$editor, options);
    }
}, {
    name: "yankNextWord",
    bindKey: "Ctrl-w",
    exec: function(iSearch) {
        var ed = iSearch.$editor,
            range = ed.selection.getRangeOfMovements(function(sel) { sel.moveCursorWordRight(); }),
            string = ed.session.getTextRange(range);
        iSearch.addString(string);
    }
}, {
    name: "yankNextChar",
    bindKey: "Ctrl-Alt-y",
    exec: function(iSearch) {
        var ed = iSearch.$editor,
            range = ed.selection.getRangeOfMovements(function(sel) { sel.moveCursorRight(); }),
            string = ed.session.getTextRange(range);
        iSearch.addString(string);
    }
}, {
    name: 'recenterTopBottom',
    bindKey: 'Ctrl-l',
    exec: function(iSearch) { iSearch.$editor.execCommand('recenterTopBottom'); }
}, {
    name: 'selectAllMatches',
    bindKey: 'Ctrl-space',
    exec: function(iSearch) {
        var ed = iSearch.$editor,
            hl = ed.session.$isearchHighlight,
            ranges = hl && hl.cache ? hl.cache
                .reduce(function(ranges, ea) {
                    return ranges.concat(ea ? ea : []); }, []) : [];
        iSearch.deactivate(false);
        ranges.forEach(ed.selection.addRange.bind(ed.selection));
    }
}, {
    name: 'searchAsRegExp',
    bindKey: 'Alt-r',
    exec: function(iSearch) {
        iSearch.convertNeedleToRegExp();
    }
}].map(function(cmd) {
    cmd.readOnly = true;
    cmd.isIncrementalSearchCommand = true;
    cmd.scrollIntoView = "animate-cursor";
    return cmd;
});

function IncrementalSearchKeyboardHandler(iSearch) {
    this.$iSearch = iSearch;
}

oop.inherits(IncrementalSearchKeyboardHandler, HashHandler);

(function() {

    this.attach = function(editor) {
        var iSearch = this.$iSearch;
        HashHandler.call(this, exports.iSearchCommands, editor.commands.platform);
        this.$commandExecHandler = editor.commands.addEventListener('exec', function(e) {
            if (!e.command.isIncrementalSearchCommand) return undefined;
            e.stopPropagation();
            e.preventDefault();
            var scrollTop = editor.session.getScrollTop();
            var result = e.command.exec(iSearch, e.args || {});
            editor.renderer.scrollCursorIntoView(null, 0.5);
            editor.renderer.animateScrolling(scrollTop);
            return result;
        });
    };

    this.detach = function(editor) {
        if (!this.$commandExecHandler) return;
        editor.commands.removeEventListener('exec', this.$commandExecHandler);
        delete this.$commandExecHandler;
    };

    var handleKeyboard$super = this.handleKeyboard;
    this.handleKeyboard = function(data, hashId, key, keyCode) {
        if (((hashId === 1/*ctrl*/ || hashId === 8/*command*/) && key === 'v')
         || (hashId === 1/*ctrl*/ && key === 'y')) return null;
        var cmd = handleKeyboard$super.call(this, data, hashId, key, keyCode);
        if (cmd.command) { return cmd; }
        if (hashId == -1) {
            var extendCmd = this.commands.extendSearchTerm;
            if (extendCmd) { return {command: extendCmd, args: key}; }
        }
        return {command: "null", passEvent: hashId == 0 || hashId == 4};
    };

}).call(IncrementalSearchKeyboardHandler.prototype);


exports.IncrementalSearchKeyboardHandler = IncrementalSearchKeyboardHandler;

});
