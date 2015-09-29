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

require("./lib/fixoldbrowsers");

var oop = require("./lib/oop");
var dom = require("./lib/dom");
var lang = require("./lib/lang");
var useragent = require("./lib/useragent");
var TextInput = require("./keyboard/textinput").TextInput;
var MouseHandler = require("./mouse/mouse_handler").MouseHandler;
var FoldHandler = require("./mouse/fold_handler").FoldHandler;
var KeyBinding = require("./keyboard/keybinding").KeyBinding;
var EditSession = require("./edit_session").EditSession;
var Search = require("./search").Search;
var Range = require("./range").Range;
var EventEmitter = require("./lib/event_emitter").EventEmitter;
var CommandManager = require("./commands/command_manager").CommandManager;
var defaultCommands = require("./commands/default_commands").commands;
var config = require("./config");
var TokenIterator = require("./token_iterator").TokenIterator;

/**
 * The main entry point into the Ace functionality.
 *
 * The `Editor` manages the [[EditSession]] (which manages [[Document]]s), as well as the [[VirtualRenderer]], which draws everything to the screen.
 *
 * Event sessions dealing with the mouse and keyboard are bubbled up from `Document` to the `Editor`, which decides what to do with them.
 * @class Editor
 **/

/**
 * Creates a new `Editor` object.
 *
 * @param {VirtualRenderer} renderer Associated `VirtualRenderer` that draws everything
 * @param {EditSession} session The `EditSession` to refer to
 *
 *
 * @constructor
 **/
var Editor = function(renderer, session) {
    var container = renderer.getContainerElement();
    this.container = container;
    this.renderer = renderer;

    this.commands = new CommandManager(useragent.isMac ? "mac" : "win", defaultCommands);
    this.textInput  = new TextInput(renderer.getTextAreaContainer(), this);
    this.renderer.textarea = this.textInput.getElement();
    this.keyBinding = new KeyBinding(this);

    // TODO detect touch event support
    this.$mouseHandler = new MouseHandler(this);
    new FoldHandler(this);

    this.$blockScrolling = 0;
    this.$search = new Search().set({
        wrap: true
    });

    this.$historyTracker = this.$historyTracker.bind(this);
    this.commands.on("exec", this.$historyTracker);

    this.$initOperationListeners();
    
    this._$emitInputEvent = lang.delayedCall(function() {
        this._signal("input", {});
        if (this.session && this.session.bgTokenizer)
            this.session.bgTokenizer.scheduleStart();
    }.bind(this));
    
    this.on("change", function(_, _self) {
        _self._$emitInputEvent.schedule(31);
    });

    this.setSession(session || new EditSession(""));
    config.resetOptions(this);
    config._signal("editor", this);
};

(function(){

    oop.implement(this, EventEmitter);

    this.$initOperationListeners = function() {
        function last(a) {return a[a.length - 1]}

        this.selections = [];
        this.commands.on("exec", this.startOperation.bind(this), true);
        this.commands.on("afterExec", this.endOperation.bind(this), true);

        this.$opResetTimer = lang.delayedCall(this.endOperation.bind(this));

        this.on("change", function() {
            this.curOp || this.startOperation();
            this.curOp.docChanged = true;
        }.bind(this), true);

        this.on("changeSelection", function() {
            this.curOp || this.startOperation();
            this.curOp.selectionChanged = true;
        }.bind(this), true);
    };

    this.curOp = null;
    this.prevOp = {};
    this.startOperation = function(commadEvent) {
        if (this.curOp) {
            if (!commadEvent || this.curOp.command)
                return;
            this.prevOp = this.curOp;
        }
        if (!commadEvent) {
            this.previousCommand = null;
            commadEvent = {};
        }

        this.$opResetTimer.schedule();
        this.curOp = {
            command: commadEvent.command || {},
            args: commadEvent.args,
            scrollTop: this.renderer.scrollTop
        };
        if (this.curOp.command.name && this.curOp.command.scrollIntoView !== undefined)
            this.$blockScrolling++;
    };

    this.endOperation = function(e) {
        if (this.curOp) {
            if (e && e.returnValue === false)
                return this.curOp = null;
            this._signal("beforeEndOperation");
            var command = this.curOp.command;
            if (command.name && this.$blockScrolling > 0)
                this.$blockScrolling--;
            var scrollIntoView = command && command.scrollIntoView;
            if (scrollIntoView) {
                switch (scrollIntoView) {
                    case "center-animate":
                        scrollIntoView = "animate";
                        /* fall through */
                    case "center":
                        this.renderer.scrollCursorIntoView(null, 0.5);
                        break;
                    case "animate":
                    case "cursor":
                        this.renderer.scrollCursorIntoView();
                        break;
                    case "selectionPart":
                        var range = this.selection.getRange();
                        var config = this.renderer.layerConfig;
                        if (range.start.row >= config.lastRow || range.end.row <= config.firstRow) {
                            this.renderer.scrollSelectionIntoView(this.selection.anchor, this.selection.lead);
                        }
                        break;
                    default:
                        break;
                }
                if (scrollIntoView == "animate")
                    this.renderer.animateScrolling(this.curOp.scrollTop);
            }
            
            this.prevOp = this.curOp;
            this.curOp = null;
        }
    };

    // TODO use property on commands instead of this
    this.$mergeableCommands = ["backspace", "del", "insertstring"];
    this.$historyTracker = function(e) {
        if (!this.$mergeUndoDeltas)
            return;

        var prev = this.prevOp;
        var mergeableCommands = this.$mergeableCommands;
        // previous command was the same
        var shouldMerge = prev.command && (e.command.name == prev.command.name);
        if (e.command.name == "insertstring") {
            var text = e.args;
            if (this.mergeNextCommand === undefined)
                this.mergeNextCommand = true;

            shouldMerge = shouldMerge
                && this.mergeNextCommand // previous command allows to coalesce with
                && (!/\s/.test(text) || /\s/.test(prev.args)); // previous insertion was of same type

            this.mergeNextCommand = true;
        } else {
            shouldMerge = shouldMerge
                && mergeableCommands.indexOf(e.command.name) !== -1; // the command is mergeable
        }

        if (
            this.$mergeUndoDeltas != "always"
            && Date.now() - this.sequenceStartTime > 2000
        ) {
            shouldMerge = false; // the sequence is too long
        }

        if (shouldMerge)
            this.session.mergeUndoDeltas = true;
        else if (mergeableCommands.indexOf(e.command.name) !== -1)
            this.sequenceStartTime = Date.now();
    };

    /**
     * Sets a new key handler, such as "vim" or "windows".
     * @param {String} keyboardHandler The new key handler
     *
     **/
    this.setKeyboardHandler = function(keyboardHandler, cb) {
        if (keyboardHandler && typeof keyboardHandler === "string") {
            this.$keybindingId = keyboardHandler;
            var _self = this;
            config.loadModule(["keybinding", keyboardHandler], function(module) {
                if (_self.$keybindingId == keyboardHandler)
                    _self.keyBinding.setKeyboardHandler(module && module.handler);
                cb && cb();
            });
        } else {
            this.$keybindingId = null;
            this.keyBinding.setKeyboardHandler(keyboardHandler);
            cb && cb();
        }
    };

    /**
     * Returns the keyboard handler, such as "vim" or "windows".
     *
     * @returns {String}
     *
     **/
    this.getKeyboardHandler = function() {
        return this.keyBinding.getKeyboardHandler();
    };


    /**
     * Emitted whenever the [[EditSession]] changes.
     * @event changeSession
     * @param {Object} e An object with two properties, `oldSession` and `session`, that represent the old and new [[EditSession]]s.
     *
     **/
    /**
     * Sets a new editsession to use. This method also emits the `'changeSession'` event.
     * @param {EditSession} session The new session to use
     *
     **/
    this.setSession = function(session) {
        if (this.session == session)
            return;
        
        // make sure operationEnd events are not emitted to wrong session
        if (this.curOp) this.endOperation();
        this.curOp = {};

        var oldSession = this.session;
        if (oldSession) {
            this.session.removeEventListener("change", this.$onDocumentChange);
            this.session.removeEventListener("changeMode", this.$onChangeMode);
            this.session.removeEventListener("tokenizerUpdate", this.$onTokenizerUpdate);
            this.session.removeEventListener("changeTabSize", this.$onChangeTabSize);
            this.session.removeEventListener("changeWrapLimit", this.$onChangeWrapLimit);
            this.session.removeEventListener("changeWrapMode", this.$onChangeWrapMode);
            this.session.removeEventListener("onChangeFold", this.$onChangeFold);
            this.session.removeEventListener("changeFrontMarker", this.$onChangeFrontMarker);
            this.session.removeEventListener("changeBackMarker", this.$onChangeBackMarker);
            this.session.removeEventListener("changeBreakpoint", this.$onChangeBreakpoint);
            this.session.removeEventListener("changeAnnotation", this.$onChangeAnnotation);
            this.session.removeEventListener("changeOverwrite", this.$onCursorChange);
            this.session.removeEventListener("changeScrollTop", this.$onScrollTopChange);
            this.session.removeEventListener("changeScrollLeft", this.$onScrollLeftChange);

            var selection = this.session.getSelection();
            selection.removeEventListener("changeCursor", this.$onCursorChange);
            selection.removeEventListener("changeSelection", this.$onSelectionChange);
        }

        this.session = session;
        if (session) {
            this.$onDocumentChange = this.onDocumentChange.bind(this);
            session.addEventListener("change", this.$onDocumentChange);
            this.renderer.setSession(session);
    
            this.$onChangeMode = this.onChangeMode.bind(this);
            session.addEventListener("changeMode", this.$onChangeMode);
    
            this.$onTokenizerUpdate = this.onTokenizerUpdate.bind(this);
            session.addEventListener("tokenizerUpdate", this.$onTokenizerUpdate);
    
            this.$onChangeTabSize = this.renderer.onChangeTabSize.bind(this.renderer);
            session.addEventListener("changeTabSize", this.$onChangeTabSize);
    
            this.$onChangeWrapLimit = this.onChangeWrapLimit.bind(this);
            session.addEventListener("changeWrapLimit", this.$onChangeWrapLimit);
    
            this.$onChangeWrapMode = this.onChangeWrapMode.bind(this);
            session.addEventListener("changeWrapMode", this.$onChangeWrapMode);
    
            this.$onChangeFold = this.onChangeFold.bind(this);
            session.addEventListener("changeFold", this.$onChangeFold);
    
            this.$onChangeFrontMarker = this.onChangeFrontMarker.bind(this);
            this.session.addEventListener("changeFrontMarker", this.$onChangeFrontMarker);
    
            this.$onChangeBackMarker = this.onChangeBackMarker.bind(this);
            this.session.addEventListener("changeBackMarker", this.$onChangeBackMarker);
    
            this.$onChangeBreakpoint = this.onChangeBreakpoint.bind(this);
            this.session.addEventListener("changeBreakpoint", this.$onChangeBreakpoint);
    
            this.$onChangeAnnotation = this.onChangeAnnotation.bind(this);
            this.session.addEventListener("changeAnnotation", this.$onChangeAnnotation);
    
            this.$onCursorChange = this.onCursorChange.bind(this);
            this.session.addEventListener("changeOverwrite", this.$onCursorChange);
    
            this.$onScrollTopChange = this.onScrollTopChange.bind(this);
            this.session.addEventListener("changeScrollTop", this.$onScrollTopChange);
    
            this.$onScrollLeftChange = this.onScrollLeftChange.bind(this);
            this.session.addEventListener("changeScrollLeft", this.$onScrollLeftChange);
    
            this.selection = session.getSelection();
            this.selection.addEventListener("changeCursor", this.$onCursorChange);
    
            this.$onSelectionChange = this.onSelectionChange.bind(this);
            this.selection.addEventListener("changeSelection", this.$onSelectionChange);
    
            this.onChangeMode();
    
            this.$blockScrolling += 1;
            this.onCursorChange();
            this.$blockScrolling -= 1;
    
            this.onScrollTopChange();
            this.onScrollLeftChange();
            this.onSelectionChange();
            this.onChangeFrontMarker();
            this.onChangeBackMarker();
            this.onChangeBreakpoint();
            this.onChangeAnnotation();
            this.session.getUseWrapMode() && this.renderer.adjustWrapLimit();
            this.renderer.updateFull();
        } else {
            this.selection = null;
            this.renderer.setSession(session);
        }

        this._signal("changeSession", {
            session: session,
            oldSession: oldSession
        });
        
        this.curOp = null;
        
        oldSession && oldSession._signal("changeEditor", {oldEditor: this});
        session && session._signal("changeEditor", {editor: this});
    };

    /**
     * Returns the current session being used.
     * @returns {EditSession}
     **/
    this.getSession = function() {
        return this.session;
    };

    /**
     * Sets the current document to `val`.
     * @param {String} val The new value to set for the document
     * @param {Number} cursorPos Where to set the new value. `undefined` or 0 is selectAll, -1 is at the document start, and 1 is at the end
     *
     * @returns {String} The current document value
     * @related Document.setValue
     **/
    this.setValue = function(val, cursorPos) {
        this.session.doc.setValue(val);

        if (!cursorPos)
            this.selectAll();
        else if (cursorPos == 1)
            this.navigateFileEnd();
        else if (cursorPos == -1)
            this.navigateFileStart();

        return val;
    };

    /**
     * Returns the current session's content.
     *
     * @returns {String}
     * @related EditSession.getValue
     **/
    this.getValue = function() {
        return this.session.getValue();
    };

    /**
     *
     * Returns the currently highlighted selection.
     * @returns {String} The highlighted selection
     **/
    this.getSelection = function() {
        return this.selection;
    };

    /**
     * {:VirtualRenderer.onResize}
     * @param {Boolean} force If `true`, recomputes the size, even if the height and width haven't changed
     *
     *
     * @related VirtualRenderer.onResize
     **/
    this.resize = function(force) {
        this.renderer.onResize(force);
    };

    /**
     * {:VirtualRenderer.setTheme}
     * @param {String} theme The path to a theme
     * @param {Function} cb optional callback called when theme is loaded
     **/
    this.setTheme = function(theme, cb) {
        this.renderer.setTheme(theme, cb);
    };

    /**
     * {:VirtualRenderer.getTheme}
     *
     * @returns {String} The set theme
     * @related VirtualRenderer.getTheme
     **/
    this.getTheme = function() {
        return this.renderer.getTheme();
    };

    /**
     * {:VirtualRenderer.setStyle}
     * @param {String} style A class name
     *
     *
     * @related VirtualRenderer.setStyle
     **/
    this.setStyle = function(style) {
        this.renderer.setStyle(style);
    };

    /**
     * {:VirtualRenderer.unsetStyle}
     * @related VirtualRenderer.unsetStyle
     **/
    this.unsetStyle = function(style) {
        this.renderer.unsetStyle(style);
    };

    /**
     * Gets the current font size of the editor text.
     */
    this.getFontSize = function () {
        return this.getOption("fontSize") ||
           dom.computedStyle(this.container, "fontSize");
    };

    /**
     * Set a new font size (in pixels) for the editor text.
     * @param {String} size A font size ( _e.g._ "12px")
     *
     *
     **/
    this.setFontSize = function(size) {
        this.setOption("fontSize", size);
    };

    this.$highlightBrackets = function() {
        if (this.session.$bracketHighlight) {
            this.session.removeMarker(this.session.$bracketHighlight);
            this.session.$bracketHighlight = null;
        }

        if (this.$highlightPending) {
            return;
        }

        // perform highlight async to not block the browser during navigation
        var self = this;
        this.$highlightPending = true;
        setTimeout(function() {
            self.$highlightPending = false;
            var session = self.session;
            if (!session || !session.bgTokenizer) return;
            var pos = session.findMatchingBracket(self.getCursorPosition());
            if (pos) {
                var range = new Range(pos.row, pos.column, pos.row, pos.column + 1);
            } else if (session.$mode.getMatching) {
                var range = session.$mode.getMatching(self.session);
            }
            if (range)
                session.$bracketHighlight = session.addMarker(range, "ace_bracket", "text");
        }, 50);
    };

    // todo: move to mode.getMatching
    this.$highlightTags = function() {
        if (this.$highlightTagPending)
            return;

        // perform highlight async to not block the browser during navigation
        var self = this;
        this.$highlightTagPending = true;
        setTimeout(function() {
            self.$highlightTagPending = false;
            
            var session = self.session;
            if (!session || !session.bgTokenizer) return;
            
            var pos = self.getCursorPosition();
            var iterator = new TokenIterator(self.session, pos.row, pos.column);
            var token = iterator.getCurrentToken();
            
            if (!token || !/\b(?:tag-open|tag-name)/.test(token.type)) {
                session.removeMarker(session.$tagHighlight);
                session.$tagHighlight = null;
                return;
            }
            
            if (token.type.indexOf("tag-open") != -1) {
                token = iterator.stepForward();
                if (!token)
                    return;
            }
            
            var tag = token.value;
            var depth = 0;
            var prevToken = iterator.stepBackward();
            
            if (prevToken.value == '<'){
                //find closing tag
                do {
                    prevToken = token;
                    token = iterator.stepForward();
                    
                    if (token && token.value === tag && token.type.indexOf('tag-name') !== -1) {
                        if (prevToken.value === '<'){
                            depth++;
                        } else if (prevToken.value === '</'){
                            depth--;
                        }
                    }
                    
                } while (token && depth >= 0);
            } else {
                //find opening tag
                do {
                    token = prevToken;
                    prevToken = iterator.stepBackward();
                    
                    if (token && token.value === tag && token.type.indexOf('tag-name') !== -1) {
                        if (prevToken.value === '<') {
                            depth++;
                        } else if (prevToken.value === '</') {
                            depth--;
                        }
                    }
                } while (prevToken && depth <= 0);
                
                //select tag again
                iterator.stepForward();
            }
            
            if (!token) {
                session.removeMarker(session.$tagHighlight);
                session.$tagHighlight = null;
                return;
            }
            
            var row = iterator.getCurrentTokenRow();
            var column = iterator.getCurrentTokenColumn();
            var range = new Range(row, column, row, column+token.value.length);
            
            //remove range if different
            if (session.$tagHighlight && range.compareRange(session.$backMarkers[session.$tagHighlight].range)!==0) {
                session.removeMarker(session.$tagHighlight);
                session.$tagHighlight = null;
            }
            
            if (range && !session.$tagHighlight)
                session.$tagHighlight = session.addMarker(range, "ace_bracket", "text");
        }, 50);
    };

    /**
     *
     * Brings the current `textInput` into focus.
     **/
    this.focus = function() {
        // Safari needs the timeout
        // iOS and Firefox need it called immediately
        // to be on the save side we do both
        var _self = this;
        setTimeout(function() {
            _self.textInput.focus();
        });
        this.textInput.focus();
    };

    /**
     * Returns `true` if the current `textInput` is in focus.
     * @return {Boolean}
     **/
    this.isFocused = function() {
        return this.textInput.isFocused();
    };

    /**
     *
     * Blurs the current `textInput`.
     **/
    this.blur = function() {
        this.textInput.blur();
    };

    /**
     * Emitted once the editor comes into focus.
     * @event focus
     *
     *
     **/
    this.onFocus = function(e) {
        if (this.$isFocused)
            return;
        this.$isFocused = true;
        this.renderer.showCursor();
        this.renderer.visualizeFocus();
        this._emit("focus", e);
    };

    /**
     * Emitted once the editor has been blurred.
     * @event blur
     *
     *
     **/
    this.onBlur = function(e) {
        if (!this.$isFocused)
            return;
        this.$isFocused = false;
        this.renderer.hideCursor();
        this.renderer.visualizeBlur();
        this._emit("blur", e);
    };

    this.$cursorChange = function() {
        this.renderer.updateCursor();
    };

    /**
     * Emitted whenever the document is changed.
     * @event change
     * @param {Object} e Contains a single property, `data`, which has the delta of changes
     *
     *
     *
     **/
    this.onDocumentChange = function(delta) {
        // Rerender and emit "change" event.
        var wrap = this.session.$useWrapMode;
        var lastRow = (delta.start.row == delta.end.row ? delta.end.row : Infinity);
        this.renderer.updateLines(delta.start.row, lastRow, wrap);

        this._signal("change", delta);
        
        // Update cursor because tab characters can influence the cursor position.
        this.$cursorChange();
        this.$updateHighlightActiveLine();
    };

    this.onTokenizerUpdate = function(e) {
        var rows = e.data;
        this.renderer.updateLines(rows.first, rows.last);
    };


    this.onScrollTopChange = function() {
        this.renderer.scrollToY(this.session.getScrollTop());
    };

    this.onScrollLeftChange = function() {
        this.renderer.scrollToX(this.session.getScrollLeft());
    };

    /**
     * Emitted when the selection changes.
     *
     **/
    this.onCursorChange = function() {
        this.$cursorChange();

        if (!this.$blockScrolling) {
            config.warn("Automatically scrolling cursor into view after selection change",
                "this will be disabled in the next version",
                "set editor.$blockScrolling = Infinity to disable this message"
            );
            this.renderer.scrollCursorIntoView();
        }

        this.$highlightBrackets();
        this.$highlightTags();
        this.$updateHighlightActiveLine();
        this._signal("changeSelection");
    };

    this.$updateHighlightActiveLine = function() {
        var session = this.getSession();

        var highlight;
        if (this.$highlightActiveLine) {
            if ((this.$selectionStyle != "line" || !this.selection.isMultiLine()))
                highlight = this.getCursorPosition();
            if (this.renderer.$maxLines && this.session.getLength() === 1 && !(this.renderer.$minLines > 1))
                highlight = false;
        }

        if (session.$highlightLineMarker && !highlight) {
            session.removeMarker(session.$highlightLineMarker.id);
            session.$highlightLineMarker = null;
        } else if (!session.$highlightLineMarker && highlight) {
            var range = new Range(highlight.row, highlight.column, highlight.row, Infinity);
            range.id = session.addMarker(range, "ace_active-line", "screenLine");
            session.$highlightLineMarker = range;
        } else if (highlight) {
            session.$highlightLineMarker.start.row = highlight.row;
            session.$highlightLineMarker.end.row = highlight.row;
            session.$highlightLineMarker.start.column = highlight.column;
            session._signal("changeBackMarker");
        }
    };

    this.onSelectionChange = function(e) {
        var session = this.session;

        if (session.$selectionMarker) {
            session.removeMarker(session.$selectionMarker);
        }
        session.$selectionMarker = null;

        if (!this.selection.isEmpty()) {
            var range = this.selection.getRange();
            var style = this.getSelectionStyle();
            session.$selectionMarker = session.addMarker(range, "ace_selection", style);
        } else {
            this.$updateHighlightActiveLine();
        }

        var re = this.$highlightSelectedWord && this.$getSelectionHighLightRegexp();
        this.session.highlight(re);

        this._signal("changeSelection");
    };

    this.$getSelectionHighLightRegexp = function() {
        var session = this.session;

        var selection = this.getSelectionRange();
        if (selection.isEmpty() || selection.isMultiLine())
            return;

        var startOuter = selection.start.column - 1;
        var endOuter = selection.end.column + 1;
        var line = session.getLine(selection.start.row);
        var lineCols = line.length;
        var needle = line.substring(Math.max(startOuter, 0),
                                    Math.min(endOuter, lineCols));

        // Make sure the outer characters are not part of the word.
        if ((startOuter >= 0 && /^[\w\d]/.test(needle)) ||
            (endOuter <= lineCols && /[\w\d]$/.test(needle)))
            return;

        needle = line.substring(selection.start.column, selection.end.column);
        if (!/^[\w\d]+$/.test(needle))
            return;

        var re = this.$search.$assembleRegExp({
            wholeWord: true,
            caseSensitive: true,
            needle: needle
        });

        return re;
    };


    this.onChangeFrontMarker = function() {
        this.renderer.updateFrontMarkers();
    };

    this.onChangeBackMarker = function() {
        this.renderer.updateBackMarkers();
    };


    this.onChangeBreakpoint = function() {
        this.renderer.updateBreakpoints();
    };

    this.onChangeAnnotation = function() {
        this.renderer.setAnnotations(this.session.getAnnotations());
    };


    this.onChangeMode = function(e) {
        this.renderer.updateText();
        this._emit("changeMode", e);
    };


    this.onChangeWrapLimit = function() {
        this.renderer.updateFull();
    };

    this.onChangeWrapMode = function() {
        this.renderer.onResize(true);
    };


    this.onChangeFold = function() {
        // Update the active line marker as due to folding changes the current
        // line range on the screen might have changed.
        this.$updateHighlightActiveLine();
        // TODO: This might be too much updating. Okay for now.
        this.renderer.updateFull();
    };

    
    /**
     * Returns the string of text currently highlighted.
     * @returns {String}
     **/
    this.getSelectedText = function() {
        return this.session.getTextRange(this.getSelectionRange());
    };
    
    /**
     * Emitted when text is copied.
     * @event copy
     * @param {String} text The copied text
     *
     **/
    /**
     * Returns the string of text currently highlighted.
     * @returns {String}
     * @deprecated Use getSelectedText instead.
     **/
    this.getCopyText = function() {
        var text = this.getSelectedText();
        this._signal("copy", text);
        return text;
    };

    /**
     * Called whenever a text "copy" happens.
     **/
    this.onCopy = function() {
        this.commands.exec("copy", this);
    };

    /**
     * Called whenever a text "cut" happens.
     **/
    this.onCut = function() {
        this.commands.exec("cut", this);
    };

    /**
     * Emitted when text is pasted.
     * @event paste
     * @param {Object} an object which contains one property, `text`, that represents the text to be pasted. Editing this property will alter the text that is pasted.
     *
     *
     **/
    /**
     * Called whenever a text "paste" happens.
     * @param {String} text The pasted text
     *
     *
     **/
    this.onPaste = function(text, event) {
        var e = {text: text, event: event};
        this.commands.exec("paste", this, e);
    };
    
    this.$handlePaste = function(e) {
        if (typeof e == "string") 
            e = {text: e};
        this._signal("paste", e);
        var text = e.text;
        if (!this.inMultiSelectMode || this.inVirtualSelectionMode) {
            this.insert(text);
        } else {
            var lines = text.split(/\r\n|\r|\n/);
            var ranges = this.selection.rangeList.ranges;
    
            if (lines.length > ranges.length || lines.length < 2 || !lines[1])
                return this.commands.exec("insertstring", this, text);
    
            for (var i = ranges.length; i--;) {
                var range = ranges[i];
                if (!range.isEmpty())
                    this.session.remove(range);
    
                this.session.insert(range.start, lines[i]);
            }
        }
    };

    this.execCommand = function(command, args) {
        return this.commands.exec(command, this, args);
    };

    /**
     * Inserts `text` into wherever the cursor is pointing.
     * @param {String} text The new text to add
     *
     **/
    this.insert = function(text, pasted) {
        var session = this.session;
        var mode = session.getMode();
        var cursor = this.getCursorPosition();

        if (this.getBehavioursEnabled() && !pasted) {
            // Get a transform if the current mode wants one.
            var transform = mode.transformAction(session.getState(cursor.row), 'insertion', this, session, text);
            if (transform) {
                if (text !== transform.text) {
                    this.session.mergeUndoDeltas = false;
                    this.$mergeNextCommand = false;
                }
                text = transform.text;

            }
        }
        
        if (text == "\t")
            text = this.session.getTabString();

        // remove selected text
        if (!this.selection.isEmpty()) {
            var range = this.getSelectionRange();
            cursor = this.session.remove(range);
            this.clearSelection();
        }
        else if (this.session.getOverwrite()) {
            var range = new Range.fromPoints(cursor, cursor);
            range.end.column += text.length;
            this.session.remove(range);
        }

        if (text == "\n" || text == "\r\n") {
            var line = session.getLine(cursor.row);
            if (cursor.column > line.search(/\S|$/)) {
                var d = line.substr(cursor.column).search(/\S|$/);
                session.doc.removeInLine(cursor.row, cursor.column, cursor.column + d);
            }
        }
        this.clearSelection();

        var start = cursor.column;
        var lineState = session.getState(cursor.row);
        var line = session.getLine(cursor.row);
        var shouldOutdent = mode.checkOutdent(lineState, line, text);
        var end = session.insert(cursor, text);

        if (transform && transform.selection) {
            if (transform.selection.length == 2) { // Transform relative to the current column
                this.selection.setSelectionRange(
                    new Range(cursor.row, start + transform.selection[0],
                              cursor.row, start + transform.selection[1]));
            } else { // Transform relative to the current row.
                this.selection.setSelectionRange(
                    new Range(cursor.row + transform.selection[0],
                              transform.selection[1],
                              cursor.row + transform.selection[2],
                              transform.selection[3]));
            }
        }

        if (session.getDocument().isNewLine(text)) {
            var lineIndent = mode.getNextLineIndent(lineState, line.slice(0, cursor.column), session.getTabString());

            session.insert({row: cursor.row+1, column: 0}, lineIndent);
        }
        if (shouldOutdent)
            mode.autoOutdent(lineState, session, cursor.row);
    };

    this.onTextInput = function(text) {
        this.keyBinding.onTextInput(text);
    };

    this.onCommandKey = function(e, hashId, keyCode) {
        this.keyBinding.onCommandKey(e, hashId, keyCode);
    };

    /**
     * Pass in `true` to enable overwrites in your session, or `false` to disable. If overwrites is enabled, any text you enter will type over any text after it. If the value of `overwrite` changes, this function also emites the `changeOverwrite` event.
     * @param {Boolean} overwrite Defines wheter or not to set overwrites
     *
     *
     * @related EditSession.setOverwrite
     **/
    this.setOverwrite = function(overwrite) {
        this.session.setOverwrite(overwrite);
    };

    /**
     * Returns `true` if overwrites are enabled; `false` otherwise.
     * @returns {Boolean}
     * @related EditSession.getOverwrite
     **/
    this.getOverwrite = function() {
        return this.session.getOverwrite();
    };

    /**
     * Sets the value of overwrite to the opposite of whatever it currently is.
     * @related EditSession.toggleOverwrite
     **/
    this.toggleOverwrite = function() {
        this.session.toggleOverwrite();
    };

    /**
     * Sets how fast the mouse scrolling should do.
     * @param {Number} speed A value indicating the new speed (in milliseconds)
     **/
    this.setScrollSpeed = function(speed) {
        this.setOption("scrollSpeed", speed);
    };

    /**
     * Returns the value indicating how fast the mouse scroll speed is (in milliseconds).
     * @returns {Number}
     **/
    this.getScrollSpeed = function() {
        return this.getOption("scrollSpeed");
    };

    /**
     * Sets the delay (in milliseconds) of the mouse drag.
     * @param {Number} dragDelay A value indicating the new delay
     **/
    this.setDragDelay = function(dragDelay) {
        this.setOption("dragDelay", dragDelay);
    };

    /**
     * Returns the current mouse drag delay.
     * @returns {Number}
     **/
    this.getDragDelay = function() {
        return this.getOption("dragDelay");
    };

    /**
     * Emitted when the selection style changes, via [[Editor.setSelectionStyle]].
     * @event changeSelectionStyle
     * @param {Object} data Contains one property, `data`, which indicates the new selection style
     **/
    /**
     * Draw selection markers spanning whole line, or only over selected text. Default value is "line"
     * @param {String} style The new selection style "line"|"text"
     *
     **/
    this.setSelectionStyle = function(val) {
        this.setOption("selectionStyle", val);
    };

    /**
     * Returns the current selection style.
     * @returns {String}
     **/
    this.getSelectionStyle = function() {
        return this.getOption("selectionStyle");
    };

    /**
     * Determines whether or not the current line should be highlighted.
     * @param {Boolean} shouldHighlight Set to `true` to highlight the current line
     **/
    this.setHighlightActiveLine = function(shouldHighlight) {
        this.setOption("highlightActiveLine", shouldHighlight);
    };
    /**
     * Returns `true` if current lines are always highlighted.
     * @return {Boolean}
     **/
    this.getHighlightActiveLine = function() {
        return this.getOption("highlightActiveLine");
    };
    this.setHighlightGutterLine = function(shouldHighlight) {
        this.setOption("highlightGutterLine", shouldHighlight);
    };

    this.getHighlightGutterLine = function() {
        return this.getOption("highlightGutterLine");
    };

    /**
     * Determines if the currently selected word should be highlighted.
     * @param {Boolean} shouldHighlight Set to `true` to highlight the currently selected word
     *
     **/
    this.setHighlightSelectedWord = function(shouldHighlight) {
        this.setOption("highlightSelectedWord", shouldHighlight);
    };

    /**
     * Returns `true` if currently highlighted words are to be highlighted.
     * @returns {Boolean}
     **/
    this.getHighlightSelectedWord = function() {
        return this.$highlightSelectedWord;
    };

    this.setAnimatedScroll = function(shouldAnimate){
        this.renderer.setAnimatedScroll(shouldAnimate);
    };

    this.getAnimatedScroll = function(){
        return this.renderer.getAnimatedScroll();
    };

    /**
     * If `showInvisibles` is set to `true`, invisible characters&mdash;like spaces or new lines&mdash;are show in the editor.
     * @param {Boolean} showInvisibles Specifies whether or not to show invisible characters
     *
     **/
    this.setShowInvisibles = function(showInvisibles) {
        this.renderer.setShowInvisibles(showInvisibles);
    };

    /**
     * Returns `true` if invisible characters are being shown.
     * @returns {Boolean}
     **/
    this.getShowInvisibles = function() {
        return this.renderer.getShowInvisibles();
    };

    this.setDisplayIndentGuides = function(display) {
        this.renderer.setDisplayIndentGuides(display);
    };

    this.getDisplayIndentGuides = function() {
        return this.renderer.getDisplayIndentGuides();
    };

    /**
     * If `showPrintMargin` is set to `true`, the print margin is shown in the editor.
     * @param {Boolean} showPrintMargin Specifies whether or not to show the print margin
     *
     **/
    this.setShowPrintMargin = function(showPrintMargin) {
        this.renderer.setShowPrintMargin(showPrintMargin);
    };

    /**
     * Returns `true` if the print margin is being shown.
     * @returns {Boolean}
     **/
    this.getShowPrintMargin = function() {
        return this.renderer.getShowPrintMargin();
    };

    /**
     * Sets the column defining where the print margin should be.
     * @param {Number} showPrintMargin Specifies the new print margin
     *
     **/
    this.setPrintMarginColumn = function(showPrintMargin) {
        this.renderer.setPrintMarginColumn(showPrintMargin);
    };

    /**
     * Returns the column number of where the print margin is.
     * @returns {Number}
     **/
    this.getPrintMarginColumn = function() {
        return this.renderer.getPrintMarginColumn();
    };

    /**
     * If `readOnly` is true, then the editor is set to read-only mode, and none of the content can change.
     * @param {Boolean} readOnly Specifies whether the editor can be modified or not
     *
     **/
    this.setReadOnly = function(readOnly) {
        this.setOption("readOnly", readOnly);
    };

    /**
     * Returns `true` if the editor is set to read-only mode.
     * @returns {Boolean}
     **/
    this.getReadOnly = function() {
        return this.getOption("readOnly");
    };

    /**
     * Specifies whether to use behaviors or not. ["Behaviors" in this case is the auto-pairing of special characters, like quotation marks, parenthesis, or brackets.]{: #BehaviorsDef}
     * @param {Boolean} enabled Enables or disables behaviors
     *
     **/
    this.setBehavioursEnabled = function (enabled) {
        this.setOption("behavioursEnabled", enabled);
    };

    /**
     * Returns `true` if the behaviors are currently enabled. {:BehaviorsDef}
     *
     * @returns {Boolean}
     **/
    this.getBehavioursEnabled = function () {
        return this.getOption("behavioursEnabled");
    };

    /**
     * Specifies whether to use wrapping behaviors or not, i.e. automatically wrapping the selection with characters such as brackets
     * when such a character is typed in.
     * @param {Boolean} enabled Enables or disables wrapping behaviors
     *
     **/
    this.setWrapBehavioursEnabled = function (enabled) {
        this.setOption("wrapBehavioursEnabled", enabled);
    };

    /**
     * Returns `true` if the wrapping behaviors are currently enabled.
     **/
    this.getWrapBehavioursEnabled = function () {
        return this.getOption("wrapBehavioursEnabled");
    };

    /**
     * Indicates whether the fold widgets should be shown or not.
     * @param {Boolean} show Specifies whether the fold widgets are shown
     **/
    this.setShowFoldWidgets = function(show) {
        this.setOption("showFoldWidgets", show);

    };
    /**
     * Returns `true` if the fold widgets are shown.
     * @return {Boolean}
     **/
    this.getShowFoldWidgets = function() {
        return this.getOption("showFoldWidgets");
    };

    this.setFadeFoldWidgets = function(fade) {
        this.setOption("fadeFoldWidgets", fade);
    };

    this.getFadeFoldWidgets = function() {
        return this.getOption("fadeFoldWidgets");
    };

    /**
     * Removes the current selection or one character.
     * @param {String} dir The direction of the deletion to occur, either "left" or "right"
     *
     **/
    this.remove = function(dir) {
        if (this.selection.isEmpty()){
            if (dir == "left")
                this.selection.selectLeft();
            else
                this.selection.selectRight();
        }

        var range = this.getSelectionRange();
        if (this.getBehavioursEnabled()) {
            var session = this.session;
            var state = session.getState(range.start.row);
            var new_range = session.getMode().transformAction(state, 'deletion', this, session, range);

            if (range.end.column === 0) {
                var text = session.getTextRange(range);
                if (text[text.length - 1] == "\n") {
                    var line = session.getLine(range.end.row);
                    if (/^\s+$/.test(line)) {
                        range.end.column = line.length;
                    }
                }
            }
            if (new_range)
                range = new_range;
        }

        this.session.remove(range);
        this.clearSelection();
    };

    /**
     * Removes the word directly to the right of the current selection.
     **/
    this.removeWordRight = function() {
        if (this.selection.isEmpty())
            this.selection.selectWordRight();

        this.session.remove(this.getSelectionRange());
        this.clearSelection();
    };

    /**
     * Removes the word directly to the left of the current selection.
     **/
    this.removeWordLeft = function() {
        if (this.selection.isEmpty())
            this.selection.selectWordLeft();

        this.session.remove(this.getSelectionRange());
        this.clearSelection();
    };

    /**
     * Removes all the words to the left of the current selection, until the start of the line.
     **/
    this.removeToLineStart = function() {
        if (this.selection.isEmpty())
            this.selection.selectLineStart();

        this.session.remove(this.getSelectionRange());
        this.clearSelection();
    };

    /**
     * Removes all the words to the right of the current selection, until the end of the line.
     **/
    this.removeToLineEnd = function() {
        if (this.selection.isEmpty())
            this.selection.selectLineEnd();

        var range = this.getSelectionRange();
        if (range.start.column == range.end.column && range.start.row == range.end.row) {
            range.end.column = 0;
            range.end.row++;
        }

        this.session.remove(range);
        this.clearSelection();
    };

    /**
     * Splits the line at the current selection (by inserting an `'\n'`).
     **/
    this.splitLine = function() {
        if (!this.selection.isEmpty()) {
            this.session.remove(this.getSelectionRange());
            this.clearSelection();
        }

        var cursor = this.getCursorPosition();
        this.insert("\n");
        this.moveCursorToPosition(cursor);
    };

    /**
     * Transposes current line.
     **/
    this.transposeLetters = function() {
        if (!this.selection.isEmpty()) {
            return;
        }

        var cursor = this.getCursorPosition();
        var column = cursor.column;
        if (column === 0)
            return;

        var line = this.session.getLine(cursor.row);
        var swap, range;
        if (column < line.length) {
            swap = line.charAt(column) + line.charAt(column-1);
            range = new Range(cursor.row, column-1, cursor.row, column+1);
        }
        else {
            swap = line.charAt(column-1) + line.charAt(column-2);
            range = new Range(cursor.row, column-2, cursor.row, column);
        }
        this.session.replace(range, swap);
    };

    /**
     * Converts the current selection entirely into lowercase.
     **/
    this.toLowerCase = function() {
        var originalRange = this.getSelectionRange();
        if (this.selection.isEmpty()) {
            this.selection.selectWord();
        }

        var range = this.getSelectionRange();
        var text = this.session.getTextRange(range);
        this.session.replace(range, text.toLowerCase());
        this.selection.setSelectionRange(originalRange);
    };

    /**
     * Converts the current selection entirely into uppercase.
     **/
    this.toUpperCase = function() {
        var originalRange = this.getSelectionRange();
        if (this.selection.isEmpty()) {
            this.selection.selectWord();
        }

        var range = this.getSelectionRange();
        var text = this.session.getTextRange(range);
        this.session.replace(range, text.toUpperCase());
        this.selection.setSelectionRange(originalRange);
    };

    /**
     * Inserts an indentation into the current cursor position or indents the selected lines.
     *
     * @related EditSession.indentRows
     **/
    this.indent = function() {
        var session = this.session;
        var range = this.getSelectionRange();

        if (range.start.row < range.end.row) {
            var rows = this.$getSelectedRows();
            session.indentRows(rows.first, rows.last, "\t");
            return;
        } else if (range.start.column < range.end.column) {
            var text = session.getTextRange(range);
            if (!/^\s+$/.test(text)) {
                var rows = this.$getSelectedRows();
                session.indentRows(rows.first, rows.last, "\t");
                return;
            }
        }
        
        var line = session.getLine(range.start.row);
        var position = range.start;
        var size = session.getTabSize();
        var column = session.documentToScreenColumn(position.row, position.column);

        if (this.session.getUseSoftTabs()) {
            var count = (size - column % size);
            var indentString = lang.stringRepeat(" ", count);
        } else {
            var count = column % size;
            while (line[range.start.column] == " " && count) {
                range.start.column--;
                count--;
            }
            this.selection.setSelectionRange(range);
            indentString = "\t";
        }
        return this.insert(indentString);
    };

    /**
     * Indents the current line.
     * @related EditSession.indentRows
     **/
    this.blockIndent = function() {
        var rows = this.$getSelectedRows();
        this.session.indentRows(rows.first, rows.last, "\t");
    };

    /**
     * Outdents the current line.
     * @related EditSession.outdentRows
     **/
    this.blockOutdent = function() {
        var selection = this.session.getSelection();
        this.session.outdentRows(selection.getRange());
    };

    // TODO: move out of core when we have good mechanism for managing extensions
    this.sortLines = function() {
        var rows = this.$getSelectedRows();
        var session = this.session;

        var lines = [];
        for (i = rows.first; i <= rows.last; i++)
            lines.push(session.getLine(i));

        lines.sort(function(a, b) {
            if (a.toLowerCase() < b.toLowerCase()) return -1;
            if (a.toLowerCase() > b.toLowerCase()) return 1;
            return 0;
        });

        var deleteRange = new Range(0, 0, 0, 0);
        for (var i = rows.first; i <= rows.last; i++) {
            var line = session.getLine(i);
            deleteRange.start.row = i;
            deleteRange.end.row = i;
            deleteRange.end.column = line.length;
            session.replace(deleteRange, lines[i-rows.first]);
        }
    };

    /**
     * Given the currently selected range, this function either comments all the lines, or uncomments all of them.
     **/
    this.toggleCommentLines = function() {
        var state = this.session.getState(this.getCursorPosition().row);
        var rows = this.$getSelectedRows();
        this.session.getMode().toggleCommentLines(state, this.session, rows.first, rows.last);
    };

    this.toggleBlockComment = function() {
        var cursor = this.getCursorPosition();
        var state = this.session.getState(cursor.row);
        var range = this.getSelectionRange();
        this.session.getMode().toggleBlockComment(state, this.session, range, cursor);
    };

    /**
     * Works like [[EditSession.getTokenAt]], except it returns a number.
     * @returns {Number}
     **/
    this.getNumberAt = function(row, column) {
        var _numberRx = /[\-]?[0-9]+(?:\.[0-9]+)?/g;
        _numberRx.lastIndex = 0;

        var s = this.session.getLine(row);
        while (_numberRx.lastIndex < column) {
            var m = _numberRx.exec(s);
            if(m.index <= column && m.index+m[0].length >= column){
                var number = {
                    value: m[0],
                    start: m.index,
                    end: m.index+m[0].length
                };
                return number;
            }
        }
        return null;
    };

    /**
     * If the character before the cursor is a number, this functions changes its value by `amount`.
     * @param {Number} amount The value to change the numeral by (can be negative to decrease value)
     *
     **/
    this.modifyNumber = function(amount) {
        var row = this.selection.getCursor().row;
        var column = this.selection.getCursor().column;

        // get the char before the cursor
        var charRange = new Range(row, column-1, row, column);

        var c = this.session.getTextRange(charRange);
        // if the char is a digit
        if (!isNaN(parseFloat(c)) && isFinite(c)) {
            // get the whole number the digit is part of
            var nr = this.getNumberAt(row, column);
            // if number found
            if (nr) {
                var fp = nr.value.indexOf(".") >= 0 ? nr.start + nr.value.indexOf(".") + 1 : nr.end;
                var decimals = nr.start + nr.value.length - fp;

                var t = parseFloat(nr.value);
                t *= Math.pow(10, decimals);


                if(fp !== nr.end && column < fp){
                    amount *= Math.pow(10, nr.end - column - 1);
                } else {
                    amount *= Math.pow(10, nr.end - column);
                }

                t += amount;
                t /= Math.pow(10, decimals);
                var nnr = t.toFixed(decimals);

                //update number
                var replaceRange = new Range(row, nr.start, row, nr.end);
                this.session.replace(replaceRange, nnr);

                //reposition the cursor
                this.moveCursorTo(row, Math.max(nr.start +1, column + nnr.length - nr.value.length));

            }
        }
    };

    /**
     * Removes all the lines in the current selection
     * @related EditSession.remove
     **/
    this.removeLines = function() {
        var rows = this.$getSelectedRows();
        this.session.removeFullLines(rows.first, rows.last);
        this.clearSelection();
    };

    this.duplicateSelection = function() {
        var sel = this.selection;
        var doc = this.session;
        var range = sel.getRange();
        var reverse = sel.isBackwards();
        if (range.isEmpty()) {
            var row = range.start.row;
            doc.duplicateLines(row, row);
        } else {
            var point = reverse ? range.start : range.end;
            var endPoint = doc.insert(point, doc.getTextRange(range), false);
            range.start = point;
            range.end = endPoint;

            sel.setSelectionRange(range, reverse);
        }
    };

    /**
     * Shifts all the selected lines down one row.
     *
     * @returns {Number} On success, it returns -1.
     * @related EditSession.moveLinesUp
     **/
    this.moveLinesDown = function() {
        this.$moveLines(1, false);
    };

    /**
     * Shifts all the selected lines up one row.
     * @returns {Number} On success, it returns -1.
     * @related EditSession.moveLinesDown
     **/
    this.moveLinesUp = function() {
        this.$moveLines(-1, false);
    };

    /**
     * Moves a range of text from the given range to the given position. `toPosition` is an object that looks like this:
     * ```json
     *    { row: newRowLocation, column: newColumnLocation }
     * ```
     * @param {Range} fromRange The range of text you want moved within the document
     * @param {Object} toPosition The location (row and column) where you want to move the text to
     *
     * @returns {Range} The new range where the text was moved to.
     * @related EditSession.moveText
     **/
    this.moveText = function(range, toPosition, copy) {
        return this.session.moveText(range, toPosition, copy);
    };

    /**
     * Copies all the selected lines up one row.
     * @returns {Number} On success, returns 0.
     *
     **/
    this.copyLinesUp = function() {
        this.$moveLines(-1, true);
    };

    /**
     * Copies all the selected lines down one row.
     * @returns {Number} On success, returns the number of new rows added; in other words, `lastRow - firstRow + 1`.
     * @related EditSession.duplicateLines
     *
     **/
    this.copyLinesDown = function() {
        this.$moveLines(1, true);
    };

    /**
     * for internal use
     * @ignore
     *
     **/
    this.$moveLines = function(dir, copy) {
        var rows, moved;
        var selection = this.selection;
        if (!selection.inMultiSelectMode || this.inVirtualSelectionMode) {
            var range = selection.toOrientedRange();
            rows = this.$getSelectedRows(range);
            moved = this.session.$moveLines(rows.first, rows.last, copy ? 0 : dir);
            if (copy && dir == -1) moved = 0;
            range.moveBy(moved, 0);
            selection.fromOrientedRange(range);
        } else {
            var ranges = selection.rangeList.ranges;
            selection.rangeList.detach(this.session);
            this.inVirtualSelectionMode = true;
            
            var diff = 0;
            var totalDiff = 0;
            var l = ranges.length;
            for (var i = 0; i < l; i++) {
                var rangeIndex = i;
                ranges[i].moveBy(diff, 0);
                rows = this.$getSelectedRows(ranges[i]);
                var first = rows.first;
                var last = rows.last;
                while (++i < l) {
                    if (totalDiff) ranges[i].moveBy(totalDiff, 0);
                    var subRows = this.$getSelectedRows(ranges[i]);
                    if (copy && subRows.first != last)
                        break;
                    else if (!copy && subRows.first > last + 1)
                        break;
                    last = subRows.last;
                }
                i--;
                diff = this.session.$moveLines(first, last, copy ? 0 : dir);
                if (copy && dir == -1) rangeIndex = i + 1;
                while (rangeIndex <= i) {
                    ranges[rangeIndex].moveBy(diff, 0);
                    rangeIndex++;
                }
                if (!copy) diff = 0;
                totalDiff += diff;
            }
            
            selection.fromOrientedRange(selection.ranges[0]);
            selection.rangeList.attach(this.session);
            this.inVirtualSelectionMode = false;
        }
    };

    /**
     * Returns an object indicating the currently selected rows. The object looks like this:
     *
     * ```json
     * { first: range.start.row, last: range.end.row }
     * ```
     *
     * @returns {Object}
     **/
    this.$getSelectedRows = function(range) {
        range = (range || this.getSelectionRange()).collapseRows();

        return {
            first: this.session.getRowFoldStart(range.start.row),
            last: this.session.getRowFoldEnd(range.end.row)
        };
    };

    this.onCompositionStart = function(text) {
        this.renderer.showComposition(this.getCursorPosition());
    };

    this.onCompositionUpdate = function(text) {
        this.renderer.setCompositionText(text);
    };

    this.onCompositionEnd = function() {
        this.renderer.hideComposition();
    };

    /**
     * {:VirtualRenderer.getFirstVisibleRow}
     *
     * @returns {Number}
     * @related VirtualRenderer.getFirstVisibleRow
     **/
    this.getFirstVisibleRow = function() {
        return this.renderer.getFirstVisibleRow();
    };

    /**
     * {:VirtualRenderer.getLastVisibleRow}
     *
     * @returns {Number}
     * @related VirtualRenderer.getLastVisibleRow
     **/
    this.getLastVisibleRow = function() {
        return this.renderer.getLastVisibleRow();
    };

    /**
     * Indicates if the row is currently visible on the screen.
     * @param {Number} row The row to check
     *
     * @returns {Boolean}
     **/
    this.isRowVisible = function(row) {
        return (row >= this.getFirstVisibleRow() && row <= this.getLastVisibleRow());
    };

    /**
     * Indicates if the entire row is currently visible on the screen.
     * @param {Number} row The row to check
     *
     *
     * @returns {Boolean}
     **/
    this.isRowFullyVisible = function(row) {
        return (row >= this.renderer.getFirstFullyVisibleRow() && row <= this.renderer.getLastFullyVisibleRow());
    };

    /**
     * Returns the number of currently visibile rows.
     * @returns {Number}
     **/
    this.$getVisibleRowCount = function() {
        return this.renderer.getScrollBottomRow() - this.renderer.getScrollTopRow() + 1;
    };

    this.$moveByPage = function(dir, select) {
        var renderer = this.renderer;
        var config = this.renderer.layerConfig;
        var rows = dir * Math.floor(config.height / config.lineHeight);

        this.$blockScrolling++;
        if (select === true) {
            this.selection.$moveSelection(function(){
                this.moveCursorBy(rows, 0);
            });
        } else if (select === false) {
            this.selection.moveCursorBy(rows, 0);
            this.selection.clearSelection();
        }
        this.$blockScrolling--;

        var scrollTop = renderer.scrollTop;

        renderer.scrollBy(0, rows * config.lineHeight);
        if (select != null)
            renderer.scrollCursorIntoView(null, 0.5);

        renderer.animateScrolling(scrollTop);
    };

    /**
     * Selects the text from the current position of the document until where a "page down" finishes.
     **/
    this.selectPageDown = function() {
        this.$moveByPage(1, true);
    };

    /**
     * Selects the text from the current position of the document until where a "page up" finishes.
     **/
    this.selectPageUp = function() {
        this.$moveByPage(-1, true);
    };

    /**
     * Shifts the document to wherever "page down" is, as well as moving the cursor position.
     **/
    this.gotoPageDown = function() {
       this.$moveByPage(1, false);
    };

    /**
     * Shifts the document to wherever "page up" is, as well as moving the cursor position.
     **/
    this.gotoPageUp = function() {
        this.$moveByPage(-1, false);
    };

    /**
     * Scrolls the document to wherever "page down" is, without changing the cursor position.
     **/
    this.scrollPageDown = function() {
        this.$moveByPage(1);
    };

    /**
     * Scrolls the document to wherever "page up" is, without changing the cursor position.
     **/
    this.scrollPageUp = function() {
        this.$moveByPage(-1);
    };

    /**
     * Moves the editor to the specified row.
     * @related VirtualRenderer.scrollToRow
     **/
    this.scrollToRow = function(row) {
        this.renderer.scrollToRow(row);
    };

    /**
     * Scrolls to a line. If `center` is `true`, it puts the line in middle of screen (or attempts to).
     * @param {Number} line The line to scroll to
     * @param {Boolean} center If `true`
     * @param {Boolean} animate If `true` animates scrolling
     * @param {Function} callback Function to be called when the animation has finished
     *
     *
     * @related VirtualRenderer.scrollToLine
     **/
    this.scrollToLine = function(line, center, animate, callback) {
        this.renderer.scrollToLine(line, center, animate, callback);
    };

    /**
     * Attempts to center the current selection on the screen.
     **/
    this.centerSelection = function() {
        var range = this.getSelectionRange();
        var pos = {
            row: Math.floor(range.start.row + (range.end.row - range.start.row) / 2),
            column: Math.floor(range.start.column + (range.end.column - range.start.column) / 2)
        };
        this.renderer.alignCursor(pos, 0.5);
    };

    /**
     * Gets the current position of the cursor.
     * @returns {Object} An object that looks something like this:
     *
     * ```json
     * { row: currRow, column: currCol }
     * ```
     *
     * @related Selection.getCursor
     **/
    this.getCursorPosition = function() {
        return this.selection.getCursor();
    };

    /**
     * Returns the screen position of the cursor.
     * @returns {Number}
     * @related EditSession.documentToScreenPosition
     **/
    this.getCursorPositionScreen = function() {
        return this.session.documentToScreenPosition(this.getCursorPosition());
    };

    /**
     * {:Selection.getRange}
     * @returns {Range}
     * @related Selection.getRange
     **/
    this.getSelectionRange = function() {
        return this.selection.getRange();
    };


    /**
     * Selects all the text in editor.
     * @related Selection.selectAll
     **/
    this.selectAll = function() {
        this.$blockScrolling += 1;
        this.selection.selectAll();
        this.$blockScrolling -= 1;
    };

    /**
     * {:Selection.clearSelection}
     * @related Selection.clearSelection
     **/
    this.clearSelection = function() {
        this.selection.clearSelection();
    };

    /**
     * Moves the cursor to the specified row and column. Note that this does not de-select the current selection.
     * @param {Number} row The new row number
     * @param {Number} column The new column number
     *
     *
     * @related Selection.moveCursorTo
     **/
    this.moveCursorTo = function(row, column) {
        this.selection.moveCursorTo(row, column);
    };

    /**
     * Moves the cursor to the position indicated by `pos.row` and `pos.column`.
     * @param {Object} pos An object with two properties, row and column
     *
     *
     * @related Selection.moveCursorToPosition
     **/
    this.moveCursorToPosition = function(pos) {
        this.selection.moveCursorToPosition(pos);
    };

    /**
     * Moves the cursor's row and column to the next matching bracket or HTML tag.
     *
     **/
    this.jumpToMatching = function(select, expand) {
        var cursor = this.getCursorPosition();
        var iterator = new TokenIterator(this.session, cursor.row, cursor.column);
        var prevToken = iterator.getCurrentToken();
        var token = prevToken || iterator.stepForward();

        if (!token) return;

        //get next closing tag or bracket
        var matchType;
        var found = false;
        var depth = {};
        var i = cursor.column - token.start;
        var bracketType;
        var brackets = {
            ")": "(",
            "(": "(",
            "]": "[",
            "[": "[",
            "{": "{",
            "}": "{"
        };
        
        do {
            if (token.value.match(/[{}()\[\]]/g)) {
                for (; i < token.value.length && !found; i++) {
                    if (!brackets[token.value[i]]) {
                        continue;
                    }

                    bracketType = brackets[token.value[i]] + '.' + token.type.replace("rparen", "lparen");

                    if (isNaN(depth[bracketType])) {
                        depth[bracketType] = 0;
                    }

                    switch (token.value[i]) {
                        case '(':
                        case '[':
                        case '{':
                            depth[bracketType]++;
                            break;
                        case ')':
                        case ']':
                        case '}':
                            depth[bracketType]--;

                            if (depth[bracketType] === -1) {
                                matchType = 'bracket';
                                found = true;
                            }
                        break;
                    }
                }
            }
            else if (token && token.type.indexOf('tag-name') !== -1) {
                if (isNaN(depth[token.value])) {
                    depth[token.value] = 0;
                }
                
                if (prevToken.value === '<') {
                    depth[token.value]++;
                }
                else if (prevToken.value === '</') {
                    depth[token.value]--;
                }
                
                if (depth[token.value] === -1) {
                    matchType = 'tag';
                    found = true;
                }
            }

            if (!found) {
                prevToken = token;
                token = iterator.stepForward();
                i = 0;
            }
        } while (token && !found);

        //no match found
        if (!matchType)
            return;

        var range, pos;
        if (matchType === 'bracket') {
            range = this.session.getBracketRange(cursor);
            if (!range) {
                range = new Range(
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + i - 1,
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + i - 1
                );
                pos = range.start;
                if (expand || pos.row === cursor.row && Math.abs(pos.column - cursor.column) < 2)
                    range = this.session.getBracketRange(pos);
            }
        }
        else if (matchType === 'tag') {
            if (token && token.type.indexOf('tag-name') !== -1) 
                var tag = token.value;
            else
                return;

            range = new Range(
                iterator.getCurrentTokenRow(),
                iterator.getCurrentTokenColumn() - 2,
                iterator.getCurrentTokenRow(),
                iterator.getCurrentTokenColumn() - 2
            );

            //find matching tag
            if (range.compare(cursor.row, cursor.column) === 0) {
                found = false;
                do {
                    token = prevToken;
                    prevToken = iterator.stepBackward();
                    
                    if (prevToken) {
                        if (prevToken.type.indexOf('tag-close') !== -1) {
                            range.setEnd(iterator.getCurrentTokenRow(), iterator.getCurrentTokenColumn() + 1);
                        }

                        if (token.value === tag && token.type.indexOf('tag-name') !== -1) {
                            if (prevToken.value === '<') {
                                depth[tag]++;
                            }
                            else if (prevToken.value === '</') {
                                depth[tag]--;
                            }
                            
                            if (depth[tag] === 0)
                                found = true;
                        }
                    }
                } while (prevToken && !found);
            }

            //we found it
            if (token && token.type.indexOf('tag-name')) {
                pos = range.start;
                if (pos.row == cursor.row && Math.abs(pos.column - cursor.column) < 2)
                    pos = range.end;
            }
        }

        pos = range && range.cursor || pos;
        if (pos) {
            if (select) {
                if (range && expand) {
                    this.selection.setRange(range);
                } else if (range && range.isEqual(this.getSelectionRange())) {
                    this.clearSelection();
                } else {
                    this.selection.selectTo(pos.row, pos.column);
                }
            } else {
                this.selection.moveTo(pos.row, pos.column);
            }
        }
    };

    /**
     * Moves the cursor to the specified line number, and also into the indiciated column.
     * @param {Number} lineNumber The line number to go to
     * @param {Number} column A column number to go to
     * @param {Boolean} animate If `true` animates scolling
     *
     **/
    this.gotoLine = function(lineNumber, column, animate) {
        this.selection.clearSelection();
        this.session.unfold({row: lineNumber - 1, column: column || 0});

        this.$blockScrolling += 1;
        // todo: find a way to automatically exit multiselect mode
        this.exitMultiSelectMode && this.exitMultiSelectMode();
        this.moveCursorTo(lineNumber - 1, column || 0);
        this.$blockScrolling -= 1;

        if (!this.isRowFullyVisible(lineNumber - 1))
            this.scrollToLine(lineNumber - 1, true, animate);
    };

    /**
     * Moves the cursor to the specified row and column. Note that this does de-select the current selection.
     * @param {Number} row The new row number
     * @param {Number} column The new column number
     *
     *
     * @related Editor.moveCursorTo
     **/
    this.navigateTo = function(row, column) {
        this.selection.moveTo(row, column);
    };

    /**
     * Moves the cursor up in the document the specified number of times. Note that this does de-select the current selection.
     * @param {Number} times The number of times to change navigation
     *
     *
     **/
    this.navigateUp = function(times) {
        if (this.selection.isMultiLine() && !this.selection.isBackwards()) {
            var selectionStart = this.selection.anchor.getPosition();
            return this.moveCursorToPosition(selectionStart);
        }
        this.selection.clearSelection();
        this.selection.moveCursorBy(-times || -1, 0);
    };

    /**
     * Moves the cursor down in the document the specified number of times. Note that this does de-select the current selection.
     * @param {Number} times The number of times to change navigation
     *
     *
     **/
    this.navigateDown = function(times) {
        if (this.selection.isMultiLine() && this.selection.isBackwards()) {
            var selectionEnd = this.selection.anchor.getPosition();
            return this.moveCursorToPosition(selectionEnd);
        }
        this.selection.clearSelection();
        this.selection.moveCursorBy(times || 1, 0);
    };

    /**
     * Moves the cursor left in the document the specified number of times. Note that this does de-select the current selection.
     * @param {Number} times The number of times to change navigation
     *
     *
     **/
    this.navigateLeft = function(times) {
        if (!this.selection.isEmpty()) {
            var selectionStart = this.getSelectionRange().start;
            this.moveCursorToPosition(selectionStart);
        }
        else {
            times = times || 1;
            while (times--) {
                this.selection.moveCursorLeft();
            }
        }
        this.clearSelection();
    };

    /**
     * Moves the cursor right in the document the specified number of times. Note that this does de-select the current selection.
     * @param {Number} times The number of times to change navigation
     *
     *
     **/
    this.navigateRight = function(times) {
        if (!this.selection.isEmpty()) {
            var selectionEnd = this.getSelectionRange().end;
            this.moveCursorToPosition(selectionEnd);
        }
        else {
            times = times || 1;
            while (times--) {
                this.selection.moveCursorRight();
            }
        }
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the start of the current line. Note that this does de-select the current selection.
     **/
    this.navigateLineStart = function() {
        this.selection.moveCursorLineStart();
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the end of the current line. Note that this does de-select the current selection.
     **/
    this.navigateLineEnd = function() {
        this.selection.moveCursorLineEnd();
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the end of the current file. Note that this does de-select the current selection.
     **/
    this.navigateFileEnd = function() {
        this.selection.moveCursorFileEnd();
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the start of the current file. Note that this does de-select the current selection.
     **/
    this.navigateFileStart = function() {
        this.selection.moveCursorFileStart();
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the word immediately to the right of the current position. Note that this does de-select the current selection.
     **/
    this.navigateWordRight = function() {
        this.selection.moveCursorWordRight();
        this.clearSelection();
    };

    /**
     *
     * Moves the cursor to the word immediately to the left of the current position. Note that this does de-select the current selection.
     **/
    this.navigateWordLeft = function() {
        this.selection.moveCursorWordLeft();
        this.clearSelection();
    };

    /**
     * Replaces the first occurance of `options.needle` with the value in `replacement`.
     * @param {String} replacement The text to replace with
     * @param {Object} options The [[Search `Search`]] options to use
     *
     *
     **/
    this.replace = function(replacement, options) {
        if (options)
            this.$search.set(options);

        var range = this.$search.find(this.session);
        var replaced = 0;
        if (!range)
            return replaced;

        if (this.$tryReplace(range, replacement)) {
            replaced = 1;
        }
        if (range !== null) {
            this.selection.setSelectionRange(range);
            this.renderer.scrollSelectionIntoView(range.start, range.end);
        }

        return replaced;
    };

    /**
     * Replaces all occurances of `options.needle` with the value in `replacement`.
     * @param {String} replacement The text to replace with
     * @param {Object} options The [[Search `Search`]] options to use
     *
     *
     **/
    this.replaceAll = function(replacement, options) {
        if (options) {
            this.$search.set(options);
        }

        var ranges = this.$search.findAll(this.session);
        var replaced = 0;
        if (!ranges.length)
            return replaced;

        this.$blockScrolling += 1;

        var selection = this.getSelectionRange();
        this.selection.moveTo(0, 0);

        for (var i = ranges.length - 1; i >= 0; --i) {
            if(this.$tryReplace(ranges[i], replacement)) {
                replaced++;
            }
        }

        this.selection.setSelectionRange(selection);
        this.$blockScrolling -= 1;

        return replaced;
    };

    this.$tryReplace = function(range, replacement) {
        var input = this.session.getTextRange(range);
        replacement = this.$search.replace(input, replacement);
        if (replacement !== null) {
            range.end = this.session.replace(range, replacement);
            return range;
        } else {
            return null;
        }
    };

    /**
     * {:Search.getOptions} For more information on `options`, see [[Search `Search`]].
     * @related Search.getOptions
     * @returns {Object}
     **/
    this.getLastSearchOptions = function() {
        return this.$search.getOptions();
    };

    /**
     * Attempts to find `needle` within the document. For more information on `options`, see [[Search `Search`]].
     * @param {String} needle The text to search for (optional)
     * @param {Object} options An object defining various search properties
     * @param {Boolean} animate If `true` animate scrolling
     *
     *
     * @related Search.find
     **/
    this.find = function(needle, options, animate) {
        if (!options)
            options = {};

        if (typeof needle == "string" || needle instanceof RegExp)
            options.needle = needle;
        else if (typeof needle == "object")
            oop.mixin(options, needle);

        var range = this.selection.getRange();
        if (options.needle == null) {
            needle = this.session.getTextRange(range)
                || this.$search.$options.needle;
            if (!needle) {
                range = this.session.getWordRange(range.start.row, range.start.column);
                needle = this.session.getTextRange(range);
            }
            this.$search.set({needle: needle});
        }

        this.$search.set(options);
        if (!options.start)
            this.$search.set({start: range});

        var newRange = this.$search.find(this.session);
        if (options.preventScroll)
            return newRange;
        if (newRange) {
            this.revealRange(newRange, animate);
            return newRange;
        }
        // clear selection if nothing is found
        if (options.backwards)
            range.start = range.end;
        else
            range.end = range.start;
        this.selection.setRange(range);
    };

    /**
     * Performs another search for `needle` in the document. For more information on `options`, see [[Search `Search`]].
     * @param {Object} options search options
     * @param {Boolean} animate If `true` animate scrolling
     *
     *
     * @related Editor.find
     **/
    this.findNext = function(options, animate) {
        this.find({skipCurrent: true, backwards: false}, options, animate);
    };

    /**
     * Performs a search for `needle` backwards. For more information on `options`, see [[Search `Search`]].
     * @param {Object} options search options
     * @param {Boolean} animate If `true` animate scrolling
     *
     *
     * @related Editor.find
     **/
    this.findPrevious = function(options, animate) {
        this.find(options, {skipCurrent: true, backwards: true}, animate);
    };

    this.revealRange = function(range, animate) {
        this.$blockScrolling += 1;
        this.session.unfold(range);
        this.selection.setSelectionRange(range);
        this.$blockScrolling -= 1;

        var scrollTop = this.renderer.scrollTop;
        this.renderer.scrollSelectionIntoView(range.start, range.end, 0.5);
        if (animate !== false)
            this.renderer.animateScrolling(scrollTop);
    };

    /**
     * {:UndoManager.undo}
     * @related UndoManager.undo
     **/
    this.undo = function() {
        this.$blockScrolling++;
        this.session.getUndoManager().undo();
        this.$blockScrolling--;
        this.renderer.scrollCursorIntoView(null, 0.5);
    };

    /**
     * {:UndoManager.redo}
     * @related UndoManager.redo
     **/
    this.redo = function() {
        this.$blockScrolling++;
        this.session.getUndoManager().redo();
        this.$blockScrolling--;
        this.renderer.scrollCursorIntoView(null, 0.5);
    };

    /**
     *
     * Cleans up the entire editor.
     **/
    this.destroy = function() {
        this.renderer.destroy();
        this._signal("destroy", this);
        if (this.session) {
            this.session.destroy();
        }
    };

    /**
     * Enables automatic scrolling of the cursor into view when editor itself is inside scrollable element
     * @param {Boolean} enable default true
     **/
    this.setAutoScrollEditorIntoView = function(enable) {
        if (!enable)
            return;
        var rect;
        var self = this;
        var shouldScroll = false;
        if (!this.$scrollAnchor)
            this.$scrollAnchor = document.createElement("div");
        var scrollAnchor = this.$scrollAnchor;
        scrollAnchor.style.cssText = "position:absolute";
        this.container.insertBefore(scrollAnchor, this.container.firstChild);
        var onChangeSelection = this.on("changeSelection", function() {
            shouldScroll = true;
        });
        // needed to not trigger sync reflow
        var onBeforeRender = this.renderer.on("beforeRender", function() {
            if (shouldScroll)
                rect = self.renderer.container.getBoundingClientRect();
        });
        var onAfterRender = this.renderer.on("afterRender", function() {
            if (shouldScroll && rect && (self.isFocused()
                || self.searchBox && self.searchBox.isFocused())
            ) {
                var renderer = self.renderer;
                var pos = renderer.$cursorLayer.$pixelPos;
                var config = renderer.layerConfig;
                var top = pos.top - config.offset;
                if (pos.top >= 0 && top + rect.top < 0) {
                    shouldScroll = true;
                } else if (pos.top < config.height &&
                    pos.top + rect.top + config.lineHeight > window.innerHeight) {
                    shouldScroll = false;
                } else {
                    shouldScroll = null;
                }
                if (shouldScroll != null) {
                    scrollAnchor.style.top = top + "px";
                    scrollAnchor.style.left = pos.left + "px";
                    scrollAnchor.style.height = config.lineHeight + "px";
                    scrollAnchor.scrollIntoView(shouldScroll);
                }
                shouldScroll = rect = null;
            }
        });
        this.setAutoScrollEditorIntoView = function(enable) {
            if (enable)
                return;
            delete this.setAutoScrollEditorIntoView;
            this.removeEventListener("changeSelection", onChangeSelection);
            this.renderer.removeEventListener("afterRender", onAfterRender);
            this.renderer.removeEventListener("beforeRender", onBeforeRender);
        };
    };


    this.$resetCursorStyle = function() {
        var style = this.$cursorStyle || "ace";
        var cursorLayer = this.renderer.$cursorLayer;
        if (!cursorLayer)
            return;
        cursorLayer.setSmoothBlinking(/smooth/.test(style));
        cursorLayer.isBlinking = !this.$readOnly && style != "wide";
        dom.setCssClass(cursorLayer.element, "ace_slim-cursors", /slim/.test(style));
    };

}).call(Editor.prototype);



config.defineOptions(Editor.prototype, "editor", {
    selectionStyle: {
        set: function(style) {
            this.onSelectionChange();
            this._signal("changeSelectionStyle", {data: style});
        },
        initialValue: "line"
    },
    highlightActiveLine: {
        set: function() {this.$updateHighlightActiveLine();},
        initialValue: true
    },
    highlightSelectedWord: {
        set: function(shouldHighlight) {this.$onSelectionChange();},
        initialValue: true
    },
    readOnly: {
        set: function(readOnly) {
            // disabled to not break vim mode!
            // this.textInput.setReadOnly(readOnly);
            this.$resetCursorStyle(); 
        },
        initialValue: false
    },
    cursorStyle: {
        set: function(val) { this.$resetCursorStyle(); },
        values: ["ace", "slim", "smooth", "wide"],
        initialValue: "ace"
    },
    mergeUndoDeltas: {
        values: [false, true, "always"],
        initialValue: true
    },
    behavioursEnabled: {initialValue: true},
    wrapBehavioursEnabled: {initialValue: true},
    autoScrollEditorIntoView: {
        set: function(val) {this.setAutoScrollEditorIntoView(val)}
    },

    hScrollBarAlwaysVisible: "renderer",
    vScrollBarAlwaysVisible: "renderer",
    highlightGutterLine: "renderer",
    animatedScroll: "renderer",
    showInvisibles: "renderer",
    showPrintMargin: "renderer",
    printMarginColumn: "renderer",
    printMargin: "renderer",
    fadeFoldWidgets: "renderer",
    showFoldWidgets: "renderer",
    showLineNumbers: "renderer",
    showGutter: "renderer",
    displayIndentGuides: "renderer",
    fontSize: "renderer",
    fontFamily: "renderer",
    maxLines: "renderer",
    minLines: "renderer",
    scrollPastEnd: "renderer",
    fixedWidthGutter: "renderer",
    theme: "renderer",

    scrollSpeed: "$mouseHandler",
    dragDelay: "$mouseHandler",
    dragEnabled: "$mouseHandler",
    focusTimout: "$mouseHandler",
    tooltipFollowsMouse: "$mouseHandler",

    firstLineNumber: "session",
    overwrite: "session",
    newLineMode: "session",
    useWorker: "session",
    useSoftTabs: "session",
    tabSize: "session",
    wrap: "session",
    indentedSoftWrap: "session",
    foldStyle: "session",
    mode: "session"
});

exports.Editor = Editor;
});
