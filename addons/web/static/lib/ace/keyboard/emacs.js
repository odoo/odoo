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

var dom = require("../lib/dom");
require("../incremental_search");
var iSearchCommandModule = require("../commands/incremental_search_commands");


var screenToTextBlockCoordinates = function(x, y) {
    var canvasPos = this.scroller.getBoundingClientRect();

    var col = Math.floor(
        (x + this.scrollLeft - canvasPos.left - this.$padding) / this.characterWidth
    );
    var row = Math.floor(
        (y + this.scrollTop - canvasPos.top) / this.lineHeight
    );

    return this.session.screenToDocumentPosition(row, col);
};

var HashHandler = require("./hash_handler").HashHandler;
exports.handler = new HashHandler();

exports.handler.isEmacs = true;
exports.handler.$id = "ace/keyboard/emacs";

var initialized = false;
var $formerLongWords;
var $formerLineStart;

exports.handler.attach = function(editor) {
    if (!initialized) {
        initialized = true;
        dom.importCssString('\
            .emacs-mode .ace_cursor{\
                border: 1px rgba(50,250,50,0.8) solid!important;\
                -moz-box-sizing: border-box!important;\
                -webkit-box-sizing: border-box!important;\
                box-sizing: border-box!important;\
                background-color: rgba(0,250,0,0.9);\
                opacity: 0.5;\
            }\
            .emacs-mode .ace_hidden-cursors .ace_cursor{\
                opacity: 1;\
                background-color: transparent;\
            }\
            .emacs-mode .ace_overwrite-cursors .ace_cursor {\
                opacity: 1;\
                background-color: transparent;\
                border-width: 0 0 2px 2px !important;\
            }\
            .emacs-mode .ace_text-layer {\
                z-index: 4\
            }\
            .emacs-mode .ace_cursor-layer {\
                z-index: 2\
            }', 'emacsMode'
        );
    }
    // in emacs, gotowordleft/right should not count a space as a word..
    $formerLongWords = editor.session.$selectLongWords;
    editor.session.$selectLongWords = true;
    // CTRL-A should go to actual beginning of line
    $formerLineStart = editor.session.$useEmacsStyleLineStart;
    editor.session.$useEmacsStyleLineStart = true;

    editor.session.$emacsMark = null; // the active mark
    editor.session.$emacsMarkRing = editor.session.$emacsMarkRing || [];

    editor.emacsMark = function() {
        return this.session.$emacsMark;
    };

    editor.setEmacsMark = function(p) {
        // to deactivate pass in a falsy value
        this.session.$emacsMark = p;
    };

    editor.pushEmacsMark = function(p, activate) {
        var prevMark = this.session.$emacsMark;
        if (prevMark)
            this.session.$emacsMarkRing.push(prevMark);
        if (!p || activate) this.setEmacsMark(p);
        else this.session.$emacsMarkRing.push(p);
    };

    editor.popEmacsMark = function() {
        var mark = this.emacsMark();
        if (mark) { this.setEmacsMark(null); return mark; }
        return this.session.$emacsMarkRing.pop();
    };

    editor.getLastEmacsMark = function(p) {
        return this.session.$emacsMark || this.session.$emacsMarkRing.slice(-1)[0];
    };

    editor.emacsMarkForSelection = function(replacement) {
        // find the mark in $emacsMarkRing corresponding to the current
        // selection
        var sel = this.selection,
            multiRangeLength = this.multiSelect ?
                this.multiSelect.getAllRanges().length : 1,
            selIndex = sel.index || 0,
            markRing = this.session.$emacsMarkRing,
            markIndex = markRing.length - (multiRangeLength - selIndex),
            lastMark = markRing[markIndex] || sel.anchor;
        if (replacement) {
            markRing.splice(markIndex, 1,
                "row" in replacement && "column" in replacement ?
                    replacement : undefined);
        }
        return lastMark;
    }

    editor.on("click", $resetMarkMode);
    editor.on("changeSession", $kbSessionChange);
    editor.renderer.screenToTextCoordinates = screenToTextBlockCoordinates;
    editor.setStyle("emacs-mode");
    editor.commands.addCommands(commands);
    exports.handler.platform = editor.commands.platform;
    editor.$emacsModeHandler = this;
    editor.addEventListener('copy', this.onCopy);
    editor.addEventListener('paste', this.onPaste);
};

exports.handler.detach = function(editor) {
    delete editor.renderer.screenToTextCoordinates;
    editor.session.$selectLongWords = $formerLongWords;
    editor.session.$useEmacsStyleLineStart = $formerLineStart;
    editor.removeEventListener("click", $resetMarkMode);
    editor.removeEventListener("changeSession", $kbSessionChange);
    editor.unsetStyle("emacs-mode");
    editor.commands.removeCommands(commands);
    editor.removeEventListener('copy', this.onCopy);
    editor.removeEventListener('paste', this.onPaste);
    editor.$emacsModeHandler = null;
};

var $kbSessionChange = function(e) {
    if (e.oldSession) {
        e.oldSession.$selectLongWords = $formerLongWords;
        e.oldSession.$useEmacsStyleLineStart = $formerLineStart;
    }

    $formerLongWords = e.session.$selectLongWords;
    e.session.$selectLongWords = true;
    $formerLineStart = e.session.$useEmacsStyleLineStart;
    e.session.$useEmacsStyleLineStart = true;

    if (!e.session.hasOwnProperty('$emacsMark'))
        e.session.$emacsMark = null;
    if (!e.session.hasOwnProperty('$emacsMarkRing'))
        e.session.$emacsMarkRing = [];
};

var $resetMarkMode = function(e) {
    e.editor.session.$emacsMark = null;
};

var keys = require("../lib/keys").KEY_MODS;
var eMods = {C: "ctrl", S: "shift", M: "alt", CMD: "command"};
var combinations = ["C-S-M-CMD",
                    "S-M-CMD", "C-M-CMD", "C-S-CMD", "C-S-M",
                    "M-CMD", "S-CMD", "S-M", "C-CMD", "C-M", "C-S",
                    "CMD", "M", "S", "C"];
combinations.forEach(function(c) {
    var hashId = 0;
    c.split("-").forEach(function(c) {
        hashId = hashId | keys[eMods[c]];
    });
    eMods[hashId] = c.toLowerCase() + "-";
});

exports.handler.onCopy = function(e, editor) {
    if (editor.$handlesEmacsOnCopy) return;
    editor.$handlesEmacsOnCopy = true;
    exports.handler.commands.killRingSave.exec(editor);
    editor.$handlesEmacsOnCopy = false;
};

exports.handler.onPaste = function(e, editor) {
    editor.pushEmacsMark(editor.getCursorPosition());
};

exports.handler.bindKey = function(key, command) {
    if (typeof key == "object")
        key = key[this.platform];
    if (!key)
        return;

    var ckb = this.commandKeyBinding;
    key.split("|").forEach(function(keyPart) {
        keyPart = keyPart.toLowerCase();
        ckb[keyPart] = command;
        // register all partial key combos as null commands
        // to be able to activate key combos with arbitrary length
        // Example: if keyPart is "C-c C-l t" then "C-c C-l t" will
        // get command assigned and "C-c" and "C-c C-l" will get
        // a null command assigned in this.commandKeyBinding. For
        // the lookup logic see handleKeyboard()
        var keyParts = keyPart.split(" ").slice(0,-1);
        keyParts.reduce(function(keyMapKeys, keyPart, i) {
            var prefix = keyMapKeys[i-1] ? keyMapKeys[i-1] + ' ' : '';
            return keyMapKeys.concat([prefix + keyPart]);
        }, []).forEach(function(keyPart) {
            if (!ckb[keyPart]) ckb[keyPart] = "null";
        });
    }, this);
};

exports.handler.getStatusText = function(editor, data) {
  var str = "";
  if (data.count)
    str += data.count;
  if (data.keyChain)
    str += " " + data.keyChain
  return str;
};

exports.handler.handleKeyboard = function(data, hashId, key, keyCode) {
    // if keyCode == -1 a non-printable key was pressed, such as just
    // control. Handling those is currently not supported in this handler
    if (keyCode === -1) return undefined;

    var editor = data.editor;
    editor._signal("changeStatus");
    // insertstring data.count times
    if (hashId == -1) {
        editor.pushEmacsMark();
        if (data.count) {
            var str = new Array(data.count + 1).join(key);
            data.count = null;
            return {command: "insertstring", args: str};
        }
    }

    var modifier = eMods[hashId];

    // CTRL + number / universalArgument for setting data.count
    if (modifier == "c-" || data.count) {
        var count = parseInt(key[key.length - 1]);
        if (typeof count === 'number' && !isNaN(count)) {
            data.count = Math.max(data.count, 0) || 0;
            data.count = 10 * data.count + count;
            return {command: "null"};
        }
    }

    // this.commandKeyBinding maps key specs like "c-p" (for CTRL + P) to
    // command objects, for lookup key needs to include the modifier
    if (modifier) key = modifier + key;

    // Key combos like CTRL+X H build up the data.keyChain
    if (data.keyChain) key = data.keyChain += " " + key;

    // Key combo prefixes get stored as "null" (String!) in this
    // this.commandKeyBinding. When encountered no command is invoked but we
    // buld up data.keyChain
    var command = this.commandKeyBinding[key];
    data.keyChain = command == "null" ? key : "";

    // there really is no command
    if (!command) return undefined;

    // we pass b/c of key combo or universalArgument
    if (command === "null") return {command: "null"};

    if (command === "universalArgument") {
        // if no number pressed emacs repeats action 4 times.
        // minus sign is needed to allow next keypress to replace it
        data.count = -4;
        return {command: "null"};
    }

    // lookup command
    // TODO extract special handling of markmode
    // TODO special case command.command is really unnecessary, remove
    var args;
    if (typeof command !== "string") {
        args = command.args;
        if (command.command) command = command.command;
        if (command === "goorselect") {
            command = editor.emacsMark() ? args[1] : args[0];
            args = null;
        }
    }

    if (typeof command === "string") {
        if (command === "insertstring" ||
            command === "splitline" ||
            command === "togglecomment") {
            editor.pushEmacsMark();
        }
        command = this.commands[command] || editor.commands.commands[command];
        if (!command) return undefined;
    }

    if (!command.readOnly && !command.isYank)
        data.lastCommand = null;

    if (!command.readOnly && editor.emacsMark())
        editor.setEmacsMark(null)
        
    if (data.count) {
        var count = data.count;
        data.count = 0;
        if (!command || !command.handlesCount) {
            return {
                args: args,
                command: {
                    exec: function(editor, args) {
                        for (var i = 0; i < count; i++)
                            command.exec(editor, args);
                    },
                    multiSelectAction: command.multiSelectAction
                }
            };
        } else {
            if (!args) args = {};
            if (typeof args === 'object') args.count = count;
        }
    }

    return {command: command, args: args};
};

exports.emacsKeys = {
    // movement
    "Up|C-p"      : {command: "goorselect", args: ["golineup","selectup"]},
    "Down|C-n"    : {command: "goorselect", args: ["golinedown","selectdown"]},
    "Left|C-b"    : {command: "goorselect", args: ["gotoleft","selectleft"]},
    "Right|C-f"   : {command: "goorselect", args: ["gotoright","selectright"]},
    "C-Left|M-b"  : {command: "goorselect", args: ["gotowordleft","selectwordleft"]},
    "C-Right|M-f" : {command: "goorselect", args: ["gotowordright","selectwordright"]},
    "Home|C-a"    : {command: "goorselect", args: ["gotolinestart","selecttolinestart"]},
    "End|C-e"     : {command: "goorselect", args: ["gotolineend","selecttolineend"]},
    "C-Home|S-M-,": {command: "goorselect", args: ["gotostart","selecttostart"]},
    "C-End|S-M-." : {command: "goorselect", args: ["gotoend","selecttoend"]},

    // selection
    "S-Up|S-C-p"      : "selectup",
    "S-Down|S-C-n"    : "selectdown",
    "S-Left|S-C-b"    : "selectleft",
    "S-Right|S-C-f"   : "selectright",
    "S-C-Left|S-M-b"  : "selectwordleft",
    "S-C-Right|S-M-f" : "selectwordright",
    "S-Home|S-C-a"    : "selecttolinestart",
    "S-End|S-C-e"     : "selecttolineend",
    "S-C-Home"        : "selecttostart",
    "S-C-End"         : "selecttoend",

    "C-l" : "recenterTopBottom",
    "M-s" : "centerselection",
    "M-g": "gotoline",
    "C-x C-p": "selectall",

    // todo fix these
    "C-Down": {command: "goorselect", args: ["gotopagedown","selectpagedown"]},
    "C-Up": {command: "goorselect", args: ["gotopageup","selectpageup"]},
    "PageDown|C-v": {command: "goorselect", args: ["gotopagedown","selectpagedown"]},
    "PageUp|M-v": {command: "goorselect", args: ["gotopageup","selectpageup"]},
    "S-C-Down": "selectpagedown",
    "S-C-Up": "selectpageup",

    "C-s": "iSearch",
    "C-r": "iSearchBackwards",

    "M-C-s": "findnext",
    "M-C-r": "findprevious",
    "S-M-5": "replace",

    // basic editing
    "Backspace": "backspace",
    "Delete|C-d": "del",
    "Return|C-m": {command: "insertstring", args: "\n"}, // "newline"
    "C-o": "splitline",

    "M-d|C-Delete": {command: "killWord", args: "right"},
    "C-Backspace|M-Backspace|M-Delete": {command: "killWord", args: "left"},
    "C-k": "killLine",

    "C-y|S-Delete": "yank",
    "M-y": "yankRotate",
    "C-g": "keyboardQuit",

    "C-w|C-S-W": "killRegion",
    "M-w": "killRingSave",
    "C-Space": "setMark",
    "C-x C-x": "exchangePointAndMark",

    "C-t": "transposeletters",
    "M-u": "touppercase",    // Doesn't work
    "M-l": "tolowercase",
    "M-/": "autocomplete",   // Doesn't work
    "C-u": "universalArgument",

    "M-;": "togglecomment",

    "C-/|C-x u|S-C--|C-z": "undo",
    "S-C-/|S-C-x u|C--|S-C-z": "redo", // infinite undo?
    // vertical editing
    "C-x r":  "selectRectangularRegion",
    "M-x": {command: "focusCommandLine", args: "M-x "}
    // todo
    // "C-x C-t" "M-t" "M-c" "F11" "C-M- "M-q"
};


exports.handler.bindKeys(exports.emacsKeys);

exports.handler.addCommands({
    recenterTopBottom: function(editor) {
        var renderer = editor.renderer;
        var pos = renderer.$cursorLayer.getPixelPosition();
        var h = renderer.$size.scrollerHeight - renderer.lineHeight;
        var scrollTop = renderer.scrollTop;
        if (Math.abs(pos.top - scrollTop) < 2) {
            scrollTop = pos.top - h;
        } else if (Math.abs(pos.top - scrollTop - h * 0.5) < 2) {
            scrollTop = pos.top;
        } else {
            scrollTop = pos.top - h * 0.5;
        }
        editor.session.setScrollTop(scrollTop);
    },
    selectRectangularRegion:  function(editor) {
        editor.multiSelect.toggleBlockSelection();
    },
    setMark:  {
        exec: function(editor, args) {
            // Sets mark-mode and clears current selection.
            // When mark is set, keyboard cursor movement commands become
            // selection modification commands. That is,
            // "goto" commands become "select" commands.
            // Any insertion or mouse click resets mark-mode.
            // setMark twice in a row at the same place resets markmode.
            // in multi select mode, ea selection is handled individually

            if (args && args.count) {
                if (editor.inMultiSelectMode) editor.forEachSelection(moveToMark);
                else moveToMark();
                moveToMark();
                return;
            }

            var mark = editor.emacsMark(),
                ranges = editor.selection.getAllRanges(),
                rangePositions = ranges.map(function(r) { return {row: r.start.row, column: r.start.column}; }),
                transientMarkModeActive = true,
                hasNoSelection = ranges.every(function(range) { return range.isEmpty(); });
            // if transientMarkModeActive then mark behavior is a little
            // different. Deactivate the mark when setMark is run with active
            // mark
            if (transientMarkModeActive && (mark || !hasNoSelection)) {
                if (editor.inMultiSelectMode) editor.forEachSelection({exec: editor.clearSelection.bind(editor)});
                else editor.clearSelection();
                if (mark) editor.pushEmacsMark(null);
                return;
            }

            if (!mark) {
                rangePositions.forEach(function(pos) { editor.pushEmacsMark(pos); });
                editor.setEmacsMark(rangePositions[rangePositions.length-1]);
                return;
            }

            // -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

            function moveToMark() {
                var mark = editor.popEmacsMark();
                mark && editor.moveCursorToPosition(mark);
            }

        },
        readOnly: true,
        handlesCount: true
    },
    exchangePointAndMark: {
        exec: function exchangePointAndMark$exec(editor, args) {
            var sel = editor.selection;
            if (!args.count && !sel.isEmpty()) { // just invert selection
                sel.setSelectionRange(sel.getRange(), !sel.isBackwards());
                return;
            }

            if (args.count) { // replace mark and point
                var pos = {row: sel.lead.row, column: sel.lead.column};
                sel.clearSelection();
                sel.moveCursorToPosition(editor.emacsMarkForSelection(pos));
            } else { // create selection to last mark
                sel.selectToPosition(editor.emacsMarkForSelection());
            }
        },
        readOnly: true,
        handlesCount: true,
        multiSelectAction: "forEach"
    },
    killWord: {
        exec: function(editor, dir) {
            editor.clearSelection();
            if (dir == "left")
                editor.selection.selectWordLeft();
            else
                editor.selection.selectWordRight();

            var range = editor.getSelectionRange();
            var text = editor.session.getTextRange(range);
            exports.killRing.add(text);

            editor.session.remove(range);
            editor.clearSelection();
        },
        multiSelectAction: "forEach"
    },
    killLine: function(editor) {
        editor.pushEmacsMark(null);
        var pos = editor.getCursorPosition();
        if (pos.column === 0 &&
            editor.session.doc.getLine(pos.row).length === 0) {
            // If an already empty line is killed, remove
            // the line entirely
            editor.selection.selectLine();
        } else {
            // otherwise just remove from the current cursor position
            // to the end (but don't delete the selection if it's before
            // the cursor)
            editor.clearSelection();
            editor.selection.selectLineEnd();
        }
        var range = editor.getSelectionRange();
        var text = editor.session.getTextRange(range);
        exports.killRing.add(text);

        editor.session.remove(range);
        editor.clearSelection();
    },
    yank: function(editor) {
        editor.onPaste(exports.killRing.get() || '');
        editor.keyBinding.$data.lastCommand = "yank";
    },
    yankRotate: function(editor) {
        if (editor.keyBinding.$data.lastCommand != "yank")
            return;
        editor.undo();
        editor.session.$emacsMarkRing.pop(); // also undo recording mark
        editor.onPaste(exports.killRing.rotate());
        editor.keyBinding.$data.lastCommand = "yank";
    },
    killRegion: {
        exec: function(editor) {
            exports.killRing.add(editor.getCopyText());
            editor.commands.byName.cut.exec(editor);
        },
        readOnly: true,
        multiSelectAction: "forEach"
    },
    killRingSave: {
        exec: function(editor) {
            // copy text and deselect. will save marks for starts of the
            // selection(s)

            editor.$handlesEmacsOnCopy = true;
            var marks = editor.session.$emacsMarkRing.slice(),
                deselectedMarks = [];
            exports.killRing.add(editor.getCopyText());

            setTimeout(function() {
                function deselect() {
                    var sel = editor.selection, range = sel.getRange(),
                        pos = sel.isBackwards() ? range.end : range.start;
                    deselectedMarks.push({row: pos.row, column: pos.column});
                    sel.clearSelection();
                }
                editor.$handlesEmacsOnCopy = false;
                if (editor.inMultiSelectMode) editor.forEachSelection({exec: deselect});
                else deselect();
                editor.session.$emacsMarkRing = marks.concat(deselectedMarks.reverse());
            }, 0);
        },
        readOnly: true
    },
    keyboardQuit: function(editor) {
        editor.selection.clearSelection();
        editor.setEmacsMark(null);
        editor.keyBinding.$data.count = null;
    },
    focusCommandLine: function(editor, arg) {
        if (editor.showCommandLine)
            editor.showCommandLine(arg);
    }
});

exports.handler.addCommands(iSearchCommandModule.iSearchStartCommands);

var commands = exports.handler.commands;
commands.yank.isYank = true;
commands.yankRotate.isYank = true;

exports.killRing = {
    $data: [],
    add: function(str) {
        str && this.$data.push(str);
        if (this.$data.length > 30)
            this.$data.shift();
    },
    get: function(n) {
        n = n || 1;
        return this.$data.slice(this.$data.length-n, this.$data.length).reverse().join('\n');
    },
    pop: function() {
        if (this.$data.length > 1)
            this.$data.pop();
        return this.get();
    },
    rotate: function() {
        this.$data.unshift(this.$data.pop());
        return this.get();
    }
};

});
