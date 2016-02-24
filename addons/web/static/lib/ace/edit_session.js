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
var lang = require("./lib/lang");
var config = require("./config");
var EventEmitter = require("./lib/event_emitter").EventEmitter;
var Selection = require("./selection").Selection;
var TextMode = require("./mode/text").Mode;
var Range = require("./range").Range;
var Document = require("./document").Document;
var BackgroundTokenizer = require("./background_tokenizer").BackgroundTokenizer;
var SearchHighlight = require("./search_highlight").SearchHighlight;

/**
 * Stores all the data about [[Editor `Editor`]] state providing easy way to change editors state.
 *
 * `EditSession` can be attached to only one [[Document `Document`]]. Same `Document` can be attached to several `EditSession`s.
 * @class EditSession
 **/

//{ events
/**
 *
 * Emitted when the document changes.
 * @event change
 * @param {Object} e An object containing a `delta` of information about the change.
 **/
/**
 * Emitted when the tab size changes, via [[EditSession.setTabSize]].
 *
 * @event changeTabSize
 **/
/**
 * Emitted when the ability to overwrite text changes, via [[EditSession.setOverwrite]].
 *
 * @event changeOverwrite
 **/
/**
 * Emitted when the gutter changes, either by setting or removing breakpoints, or when the gutter decorations change.
 *
 * @event changeBreakpoint
 **/
/**
 * Emitted when a front marker changes.
 *
 * @event changeFrontMarker
 **/
/**
 * Emitted when a back marker changes.
 *
 * @event changeBackMarker
 **/
/**
 * Emitted when an annotation changes, like through [[EditSession.setAnnotations]].
 *
 * @event changeAnnotation
 **/
/**
 * Emitted when a background tokenizer asynchronously processes new rows.
 * @event tokenizerUpdate
 *
 * @param {Object} e An object containing one property, `"data"`, that contains information about the changing rows
 *
 **/
/**
 * Emitted when the current mode changes.
 *
 * @event changeMode
 *
 **/
/**
 * Emitted when the wrap mode changes.
 *
 * @event changeWrapMode
 *
 **/
/**
 * Emitted when the wrapping limit changes.
 *
 * @event changeWrapLimit
 *
 **/
/**
 * Emitted when a code fold is added or removed.
 *
 * @event changeFold
 *
 **/
 /**
 * Emitted when the scroll top changes.
 * @event changeScrollTop
 *
 * @param {Number} scrollTop The new scroll top value
 **/
/**
 * Emitted when the scroll left changes.
 * @event changeScrollLeft
 *
 * @param {Number} scrollLeft The new scroll left value
 **/
//}

/**
 *
 * Sets up a new `EditSession` and associates it with the given `Document` and `TextMode`.
 * @param {Document | String} text [If `text` is a `Document`, it associates the `EditSession` with it. Otherwise, a new `Document` is created, with the initial text]{: #textParam}
 * @param {TextMode} mode [The inital language mode to use for the document]{: #modeParam}
 *
 * @constructor
 **/

var EditSession = function(text, mode) {
    this.$breakpoints = [];
    this.$decorations = [];
    this.$frontMarkers = {};
    this.$backMarkers = {};
    this.$markerId = 1;
    this.$undoSelect = true;

    this.$foldData = [];
    this.$foldData.toString = function() {
        return this.join("\n");
    };
    this.on("changeFold", this.onChangeFold.bind(this));
    this.$onChange = this.onChange.bind(this);

    if (typeof text != "object" || !text.getLine)
        text = new Document(text);

    this.setDocument(text);
    this.selection = new Selection(this);

    config.resetOptions(this);
    this.setMode(mode);
    config._signal("session", this);
};


(function() {

    oop.implement(this, EventEmitter);

    /**
     * Sets the `EditSession` to point to a new `Document`. If a `BackgroundTokenizer` exists, it also points to `doc`.
     *
     * @param {Document} doc The new `Document` to use
     *
     **/
    this.setDocument = function(doc) {
        if (this.doc)
            this.doc.removeListener("change", this.$onChange);

        this.doc = doc;
        doc.on("change", this.$onChange);

        if (this.bgTokenizer)
            this.bgTokenizer.setDocument(this.getDocument());

        this.resetCaches();
    };

    /**
     * Returns the `Document` associated with this session.
     * @return {Document}
     **/
    this.getDocument = function() {
        return this.doc;
    };

    /**
     * @param {Number} row The row to work with
     *
     **/
    this.$resetRowCache = function(docRow) {
        if (!docRow) {
            this.$docRowCache = [];
            this.$screenRowCache = [];
            return;
        }
        var l = this.$docRowCache.length;
        var i = this.$getRowCacheIndex(this.$docRowCache, docRow) + 1;
        if (l > i) {
            this.$docRowCache.splice(i, l);
            this.$screenRowCache.splice(i, l);
        }
    };

    this.$getRowCacheIndex = function(cacheArray, val) {
        var low = 0;
        var hi = cacheArray.length - 1;

        while (low <= hi) {
            var mid = (low + hi) >> 1;
            var c = cacheArray[mid];

            if (val > c)
                low = mid + 1;
            else if (val < c)
                hi = mid - 1;
            else
                return mid;
        }

        return low -1;
    };

    this.resetCaches = function() {
        this.$modified = true;
        this.$wrapData = [];
        this.$rowLengthCache = [];
        this.$resetRowCache(0);
        if (this.bgTokenizer)
            this.bgTokenizer.start(0);
    };

    this.onChangeFold = function(e) {
        var fold = e.data;
        this.$resetRowCache(fold.start.row);
    };

    this.onChange = function(delta) {
        this.$modified = true;

        this.$resetRowCache(delta.start.row);

        var removedFolds = this.$updateInternalDataOnChange(delta);
        if (!this.$fromUndo && this.$undoManager && !delta.ignore) {
            this.$deltasDoc.push(delta);
            if (removedFolds && removedFolds.length != 0) {
                this.$deltasFold.push({
                    action: "removeFolds",
                    folds:  removedFolds
                });
            }

            this.$informUndoManager.schedule();
        }

        this.bgTokenizer && this.bgTokenizer.$updateOnChange(delta);
        this._signal("change", delta);
    };

    /**
    * Sets the session text.
    * @param {String} text The new text to place
    *
    **/
    this.setValue = function(text) {
        this.doc.setValue(text);
        this.selection.moveTo(0, 0);

        this.$resetRowCache(0);
        this.$deltas = [];
        this.$deltasDoc = [];
        this.$deltasFold = [];
        this.setUndoManager(this.$undoManager);
        this.getUndoManager().reset();
    };

    /**
    * Returns the current [[Document `Document`]] as a string.
    * @method toString
    * @returns {String}
    * @alias EditSession.getValue
    *
    **/

    /**
    * Returns the current [[Document `Document`]] as a string.
    * @method getValue
    * @returns {String}
    * @alias EditSession.toString
    **/
    this.getValue =
    this.toString = function() {
        return this.doc.getValue();
    };

    /**
    * Returns the string of the current selection.
    **/
    this.getSelection = function() {
        return this.selection;
    };

    /**
     * {:BackgroundTokenizer.getState}
     * @param {Number} row The row to start at
     *
     * @related BackgroundTokenizer.getState
     **/
    this.getState = function(row) {
        return this.bgTokenizer.getState(row);
    };

    /**
     * Starts tokenizing at the row indicated. Returns a list of objects of the tokenized rows.
     * @param {Number} row The row to start at
     *
     *
     *
     **/
    this.getTokens = function(row) {
        return this.bgTokenizer.getTokens(row);
    };

    /**
    * Returns an object indicating the token at the current row. The object has two properties: `index` and `start`.
    * @param {Number} row The row number to retrieve from
    * @param {Number} column The column number to retrieve from
    *
    *
    **/
    this.getTokenAt = function(row, column) {
        var tokens = this.bgTokenizer.getTokens(row);
        var token, c = 0;
        if (column == null) {
            i = tokens.length - 1;
            c = this.getLine(row).length;
        } else {
            for (var i = 0; i < tokens.length; i++) {
                c += tokens[i].value.length;
                if (c >= column)
                    break;
            }
        }
        token = tokens[i];
        if (!token)
            return null;
        token.index = i;
        token.start = c - token.value.length;
        return token;
    };

    /**
    * Sets the undo manager.
    * @param {UndoManager} undoManager The new undo manager
    *
    *
    **/
    this.setUndoManager = function(undoManager) {
        this.$undoManager = undoManager;
        this.$deltas = [];
        this.$deltasDoc = [];
        this.$deltasFold = [];

        if (this.$informUndoManager)
            this.$informUndoManager.cancel();

        if (undoManager) {
            var self = this;

            this.$syncInformUndoManager = function() {
                self.$informUndoManager.cancel();

                if (self.$deltasFold.length) {
                    self.$deltas.push({
                        group: "fold",
                        deltas: self.$deltasFold
                    });
                    self.$deltasFold = [];
                }

                if (self.$deltasDoc.length) {
                    self.$deltas.push({
                        group: "doc",
                        deltas: self.$deltasDoc
                    });
                    self.$deltasDoc = [];
                }

                if (self.$deltas.length > 0) {
                    undoManager.execute({
                        action: "aceupdate",
                        args: [self.$deltas, self],
                        merge: self.mergeUndoDeltas
                    });
                }
                self.mergeUndoDeltas = false;
                self.$deltas = [];
            };
            this.$informUndoManager = lang.delayedCall(this.$syncInformUndoManager);
        }
    };

    /**
     * starts a new group in undo history
     **/
    this.markUndoGroup = function() {
        if (this.$syncInformUndoManager)
            this.$syncInformUndoManager();
    };
    
    this.$defaultUndoManager = {
        undo: function() {},
        redo: function() {},
        reset: function() {}
    };

    /**
    * Returns the current undo manager.
    **/
    this.getUndoManager = function() {
        return this.$undoManager || this.$defaultUndoManager;
    };

    /**
    * Returns the current value for tabs. If the user is using soft tabs, this will be a series of spaces (defined by [[EditSession.getTabSize `getTabSize()`]]); otherwise it's simply `'\t'`.
    **/
    this.getTabString = function() {
        if (this.getUseSoftTabs()) {
            return lang.stringRepeat(" ", this.getTabSize());
        } else {
            return "\t";
        }
    };

    /**
    /**
    * Pass `true` to enable the use of soft tabs. Soft tabs means you're using spaces instead of the tab character (`'\t'`).
    * @param {Boolean} useSoftTabs Value indicating whether or not to use soft tabs
    **/
    this.setUseSoftTabs = function(val) {
        this.setOption("useSoftTabs", val);
    };
    /**
    * Returns `true` if soft tabs are being used, `false` otherwise.
    * @returns {Boolean}
    **/
    this.getUseSoftTabs = function() {
        // todo might need more general way for changing settings from mode, but this is ok for now
        return this.$useSoftTabs && !this.$mode.$indentWithTabs;
    };
    /**
    * Set the number of spaces that define a soft tab; for example, passing in `4` transforms the soft tabs to be equivalent to four spaces. This function also emits the `changeTabSize` event.
    * @param {Number} tabSize The new tab size
    **/
    this.setTabSize = function(tabSize) {
        this.setOption("tabSize", tabSize);
    };
    /**
    * Returns the current tab size.
    **/
    this.getTabSize = function() {
        return this.$tabSize;
    };

    /**
    * Returns `true` if the character at the position is a soft tab.
    * @param {Object} position The position to check
    *
    *
    **/
    this.isTabStop = function(position) {
        return this.$useSoftTabs && (position.column % this.$tabSize === 0);
    };

    this.$overwrite = false;
    /**
    * Pass in `true` to enable overwrites in your session, or `false` to disable.
    *
    * If overwrites is enabled, any text you enter will type over any text after it. If the value of `overwrite` changes, this function also emites the `changeOverwrite` event.
    *
    * @param {Boolean} overwrite Defines wheter or not to set overwrites
    *
    *
    **/
    this.setOverwrite = function(overwrite) {
        this.setOption("overwrite", overwrite);
    };

    /**
    * Returns `true` if overwrites are enabled; `false` otherwise.
    **/
    this.getOverwrite = function() {
        return this.$overwrite;
    };

    /**
    * Sets the value of overwrite to the opposite of whatever it currently is.
    **/
    this.toggleOverwrite = function() {
        this.setOverwrite(!this.$overwrite);
    };

    /**
    * Adds `className` to the `row`, to be used for CSS stylings and whatnot.
    * @param {Number} row The row number
    * @param {String} className The class to add
    *
    *
    **/
    this.addGutterDecoration = function(row, className) {
        if (!this.$decorations[row])
            this.$decorations[row] = "";
        this.$decorations[row] += " " + className;
        this._signal("changeBreakpoint", {});
    };

    /**
    * Removes `className` from the `row`.
    * @param {Number} row The row number
    * @param {String} className The class to add
    *
    *
    **/
    this.removeGutterDecoration = function(row, className) {
        this.$decorations[row] = (this.$decorations[row] || "").replace(" " + className, "");
        this._signal("changeBreakpoint", {});
    };

    /**
    * Returns an array of numbers, indicating which rows have breakpoints.
    * @returns {[Number]}
    **/
    this.getBreakpoints = function() {
        return this.$breakpoints;
    };

    /**
    * Sets a breakpoint on every row number given by `rows`. This function also emites the `'changeBreakpoint'` event.
    * @param {Array} rows An array of row indices
    *
    *
    *
    **/
    this.setBreakpoints = function(rows) {
        this.$breakpoints = [];
        for (var i=0; i<rows.length; i++) {
            this.$breakpoints[rows[i]] = "ace_breakpoint";
        }
        this._signal("changeBreakpoint", {});
    };

    /**
    * Removes all breakpoints on the rows. This function also emites the `'changeBreakpoint'` event.
    **/
    this.clearBreakpoints = function() {
        this.$breakpoints = [];
        this._signal("changeBreakpoint", {});
    };

    /**
    * Sets a breakpoint on the row number given by `rows`. This function also emites the `'changeBreakpoint'` event.
    * @param {Number} row A row index
    * @param {String} className Class of the breakpoint
    *
    *
    **/
    this.setBreakpoint = function(row, className) {
        if (className === undefined)
            className = "ace_breakpoint";
        if (className)
            this.$breakpoints[row] = className;
        else
            delete this.$breakpoints[row];
        this._signal("changeBreakpoint", {});
    };

    /**
    * Removes a breakpoint on the row number given by `rows`. This function also emites the `'changeBreakpoint'` event.
    * @param {Number} row A row index
    *
    *
    **/
    this.clearBreakpoint = function(row) {
        delete this.$breakpoints[row];
        this._signal("changeBreakpoint", {});
    };

    /**
    * Adds a new marker to the given `Range`. If `inFront` is `true`, a front marker is defined, and the `'changeFrontMarker'` event fires; otherwise, the `'changeBackMarker'` event fires.
    * @param {Range} range Define the range of the marker
    * @param {String} clazz Set the CSS class for the marker
    * @param {Function | String} type Identify the type of the marker
    * @param {Boolean} inFront Set to `true` to establish a front marker
    *
    *
    * @return {Number} The new marker id
    **/
    this.addMarker = function(range, clazz, type, inFront) {
        var id = this.$markerId++;

        var marker = {
            range : range,
            type : type || "line",
            renderer: typeof type == "function" ? type : null,
            clazz : clazz,
            inFront: !!inFront,
            id: id
        };

        if (inFront) {
            this.$frontMarkers[id] = marker;
            this._signal("changeFrontMarker");
        } else {
            this.$backMarkers[id] = marker;
            this._signal("changeBackMarker");
        }

        return id;
    };

    /**
     * Adds a dynamic marker to the session.
     * @param {Object} marker object with update method
     * @param {Boolean} inFront Set to `true` to establish a front marker
     *
     *
     * @return {Object} The added marker
     **/
    this.addDynamicMarker = function(marker, inFront) {
        if (!marker.update)
            return;
        var id = this.$markerId++;
        marker.id = id;
        marker.inFront = !!inFront;

        if (inFront) {
            this.$frontMarkers[id] = marker;
            this._signal("changeFrontMarker");
        } else {
            this.$backMarkers[id] = marker;
            this._signal("changeBackMarker");
        }

        return marker;
    };

    /**
    * Removes the marker with the specified ID. If this marker was in front, the `'changeFrontMarker'` event is emitted. If the marker was in the back, the `'changeBackMarker'` event is emitted.
    * @param {Number} markerId A number representing a marker
    *
    *
    *
    **/
    this.removeMarker = function(markerId) {
        var marker = this.$frontMarkers[markerId] || this.$backMarkers[markerId];
        if (!marker)
            return;

        var markers = marker.inFront ? this.$frontMarkers : this.$backMarkers;
        if (marker) {
            delete (markers[markerId]);
            this._signal(marker.inFront ? "changeFrontMarker" : "changeBackMarker");
        }
    };

    /**
    * Returns an object containing all of the markers, either front or back.
    * @param {Boolean} inFront If `true`, indicates you only want front markers; `false` indicates only back markers
    *
    * @returns {Object}
    **/
    this.getMarkers = function(inFront) {
        return inFront ? this.$frontMarkers : this.$backMarkers;
    };

    this.highlight = function(re) {
        if (!this.$searchHighlight) {
            var highlight = new SearchHighlight(null, "ace_selected-word", "text");
            this.$searchHighlight = this.addDynamicMarker(highlight);
        }
        this.$searchHighlight.setRegexp(re);
    };

    // experimental
    this.highlightLines = function(startRow, endRow, clazz, inFront) {
        if (typeof endRow != "number") {
            clazz = endRow;
            endRow = startRow;
        }
        if (!clazz)
            clazz = "ace_step";

        var range = new Range(startRow, 0, endRow, Infinity);
        range.id = this.addMarker(range, clazz, "fullLine", inFront);
        return range;
    };

    /*
     * Error:
     *  {
     *    row: 12,
     *    column: 2, //can be undefined
     *    text: "Missing argument",
     *    type: "error" // or "warning" or "info"
     *  }
     */
    /**
    * Sets annotations for the `EditSession`. This functions emits the `'changeAnnotation'` event.
    * @param {Array} annotations A list of annotations
    *
    **/
    this.setAnnotations = function(annotations) {
        this.$annotations = annotations;
        this._signal("changeAnnotation", {});
    };

    /**
    * Returns the annotations for the `EditSession`.
    * @returns {Array}
    **/
    this.getAnnotations = function() {
        return this.$annotations || [];
    };

    /**
    * Clears all the annotations for this session. This function also triggers the `'changeAnnotation'` event.
    **/
    this.clearAnnotations = function() {
        this.setAnnotations([]);
    };

    /**
    * If `text` contains either the newline (`\n`) or carriage-return ('\r') characters, `$autoNewLine` stores that value.
    * @param {String} text A block of text
    *
    *
    **/
    this.$detectNewLine = function(text) {
        var match = text.match(/^.*?(\r?\n)/m);
        if (match) {
            this.$autoNewLine = match[1];
        } else {
            this.$autoNewLine = "\n";
        }
    };

    /**
    * Given a starting row and column, this method returns the `Range` of the first word boundary it finds.
    * @param {Number} row The row to start at
    * @param {Number} column The column to start at
    *
    * @returns {Range}
    **/
    this.getWordRange = function(row, column) {
        var line = this.getLine(row);

        var inToken = false;
        if (column > 0)
            inToken = !!line.charAt(column - 1).match(this.tokenRe);

        if (!inToken)
            inToken = !!line.charAt(column).match(this.tokenRe);

        if (inToken)
            var re = this.tokenRe;
        else if (/^\s+$/.test(line.slice(column-1, column+1)))
            var re = /\s/;
        else
            var re = this.nonTokenRe;

        var start = column;
        if (start > 0) {
            do {
                start--;
            }
            while (start >= 0 && line.charAt(start).match(re));
            start++;
        }

        var end = column;
        while (end < line.length && line.charAt(end).match(re)) {
            end++;
        }

        return new Range(row, start, row, end);
    };

    /**
    * Gets the range of a word, including its right whitespace.
    * @param {Number} row The row number to start from
    * @param {Number} column The column number to start from
    *
    * @return {Range}
    **/
    this.getAWordRange = function(row, column) {
        var wordRange = this.getWordRange(row, column);
        var line = this.getLine(wordRange.end.row);

        while (line.charAt(wordRange.end.column).match(/[ \t]/)) {
            wordRange.end.column += 1;
        }
        return wordRange;
    };

    /**
    * {:Document.setNewLineMode.desc}
    * @param {String} newLineMode {:Document.setNewLineMode.param}
    *
    *
    * @related Document.setNewLineMode
    **/
    this.setNewLineMode = function(newLineMode) {
        this.doc.setNewLineMode(newLineMode);
    };

    /**
    *
    * Returns the current new line mode.
    * @returns {String}
    * @related Document.getNewLineMode
    **/
    this.getNewLineMode = function() {
        return this.doc.getNewLineMode();
    };

    /**
    * Identifies if you want to use a worker for the `EditSession`.
    * @param {Boolean} useWorker Set to `true` to use a worker
    *
    **/
    this.setUseWorker = function(useWorker) { this.setOption("useWorker", useWorker); };

    /**
    * Returns `true` if workers are being used.
    **/
    this.getUseWorker = function() { return this.$useWorker; };

    /**
    * Reloads all the tokens on the current session. This function calls [[BackgroundTokenizer.start `BackgroundTokenizer.start ()`]] to all the rows; it also emits the `'tokenizerUpdate'` event.
    **/
    this.onReloadTokenizer = function(e) {
        var rows = e.data;
        this.bgTokenizer.start(rows.first);
        this._signal("tokenizerUpdate", e);
    };

    this.$modes = {};

    /**
    * Sets a new text mode for the `EditSession`. This method also emits the `'changeMode'` event. If a [[BackgroundTokenizer `BackgroundTokenizer`]] is set, the `'tokenizerUpdate'` event is also emitted.
    * @param {TextMode} mode Set a new text mode
    * @param {cb} optional callback
    *
    **/
    this.$mode = null;
    this.$modeId = null;
    this.setMode = function(mode, cb) {
        if (mode && typeof mode === "object") {
            if (mode.getTokenizer)
                return this.$onChangeMode(mode);
            var options = mode;
            var path = options.path;
        } else {
            path = mode || "ace/mode/text";
        }

        // this is needed if ace isn't on require path (e.g tests in node)
        if (!this.$modes["ace/mode/text"])
            this.$modes["ace/mode/text"] = new TextMode();

        if (this.$modes[path] && !options) {
            this.$onChangeMode(this.$modes[path]);
            cb && cb();
            return;
        }
        // load on demand
        this.$modeId = path;
        config.loadModule(["mode", path], function(m) {
            if (this.$modeId !== path)
                return cb && cb();
            if (this.$modes[path] && !options) {
                this.$onChangeMode(this.$modes[path]);
            } else if (m && m.Mode) {
                m = new m.Mode(options);
                if (!options) {
                    this.$modes[path] = m;
                    m.$id = path;
                }
                this.$onChangeMode(m);
            }
            cb && cb();
        }.bind(this));

        // set mode to text until loading is finished
        if (!this.$mode)
            this.$onChangeMode(this.$modes["ace/mode/text"], true);
    };

    this.$onChangeMode = function(mode, $isPlaceholder) {
        if (!$isPlaceholder)
            this.$modeId = mode.$id;
        if (this.$mode === mode) 
            return;

        this.$mode = mode;

        this.$stopWorker();

        if (this.$useWorker)
            this.$startWorker();

        var tokenizer = mode.getTokenizer();

        if(tokenizer.addEventListener !== undefined) {
            var onReloadTokenizer = this.onReloadTokenizer.bind(this);
            tokenizer.addEventListener("update", onReloadTokenizer);
        }

        if (!this.bgTokenizer) {
            this.bgTokenizer = new BackgroundTokenizer(tokenizer);
            var _self = this;
            this.bgTokenizer.addEventListener("update", function(e) {
                _self._signal("tokenizerUpdate", e);
            });
        } else {
            this.bgTokenizer.setTokenizer(tokenizer);
        }

        this.bgTokenizer.setDocument(this.getDocument());

        this.tokenRe = mode.tokenRe;
        this.nonTokenRe = mode.nonTokenRe;

        
        if (!$isPlaceholder) {
            // experimental method, used by c9 findiniles
            if (mode.attachToSession)
                mode.attachToSession(this);
            this.$options.wrapMethod.set.call(this, this.$wrapMethod);
            this.$setFolding(mode.foldingRules);
            this.bgTokenizer.start(0);
            this._emit("changeMode");
        }
    };

    this.$stopWorker = function() {
        if (this.$worker) {
            this.$worker.terminate();
            this.$worker = null;
        }
    };

    this.$startWorker = function() {
        try {
            this.$worker = this.$mode.createWorker(this);
        } catch (e) {
            config.warn("Could not load worker", e);
            this.$worker = null;
        }
    };

    /**
    * Returns the current text mode.
    * @returns {TextMode} The current text mode
    **/
    this.getMode = function() {
        return this.$mode;
    };

    this.$scrollTop = 0;
    /**
    * This function sets the scroll top value. It also emits the `'changeScrollTop'` event.
    * @param {Number} scrollTop The new scroll top value
    *
    **/
    this.setScrollTop = function(scrollTop) {
        // TODO: should we force integer lineheight instead? scrollTop = Math.round(scrollTop); 
        if (this.$scrollTop === scrollTop || isNaN(scrollTop))
            return;

        this.$scrollTop = scrollTop;
        this._signal("changeScrollTop", scrollTop);
    };

    /**
    * [Returns the value of the distance between the top of the editor and the topmost part of the visible content.]{: #EditSession.getScrollTop}
    * @returns {Number}
    **/
    this.getScrollTop = function() {
        return this.$scrollTop;
    };

    this.$scrollLeft = 0;
    /**
    * [Sets the value of the distance between the left of the editor and the leftmost part of the visible content.]{: #EditSession.setScrollLeft}
    **/
    this.setScrollLeft = function(scrollLeft) {
        // scrollLeft = Math.round(scrollLeft);
        if (this.$scrollLeft === scrollLeft || isNaN(scrollLeft))
            return;

        this.$scrollLeft = scrollLeft;
        this._signal("changeScrollLeft", scrollLeft);
    };

    /**
    * [Returns the value of the distance between the left of the editor and the leftmost part of the visible content.]{: #EditSession.getScrollLeft}
    * @returns {Number}
    **/
    this.getScrollLeft = function() {
        return this.$scrollLeft;
    };

    /**
    * Returns the width of the screen.
    * @returns {Number}
    **/
    this.getScreenWidth = function() {
        this.$computeWidth();
        if (this.lineWidgets) 
            return Math.max(this.getLineWidgetMaxWidth(), this.screenWidth);
        return this.screenWidth;
    };
    
    this.getLineWidgetMaxWidth = function() {
        if (this.lineWidgetsWidth != null) return this.lineWidgetsWidth;
        var width = 0;
        this.lineWidgets.forEach(function(w) {
            if (w && w.screenWidth > width)
                width = w.screenWidth;
        });
        return this.lineWidgetWidth = width;
    };

    this.$computeWidth = function(force) {
        if (this.$modified || force) {
            this.$modified = false;

            if (this.$useWrapMode)
                return this.screenWidth = this.$wrapLimit;

            var lines = this.doc.getAllLines();
            var cache = this.$rowLengthCache;
            var longestScreenLine = 0;
            var foldIndex = 0;
            var foldLine = this.$foldData[foldIndex];
            var foldStart = foldLine ? foldLine.start.row : Infinity;
            var len = lines.length;

            for (var i = 0; i < len; i++) {
                if (i > foldStart) {
                    i = foldLine.end.row + 1;
                    if (i >= len)
                        break;
                    foldLine = this.$foldData[foldIndex++];
                    foldStart = foldLine ? foldLine.start.row : Infinity;
                }

                if (cache[i] == null)
                    cache[i] = this.$getStringScreenWidth(lines[i])[0];

                if (cache[i] > longestScreenLine)
                    longestScreenLine = cache[i];
            }
            this.screenWidth = longestScreenLine;
        }
    };

    /**
     * Returns a verbatim copy of the given line as it is in the document
     * @param {Number} row The row to retrieve from
     *
    *
     * @returns {String}
    *
    **/
    this.getLine = function(row) {
        return this.doc.getLine(row);
    };

    /**
     * Returns an array of strings of the rows between `firstRow` and `lastRow`. This function is inclusive of `lastRow`.
     * @param {Number} firstRow The first row index to retrieve
     * @param {Number} lastRow The final row index to retrieve
     *
     * @returns {[String]}
     *
     **/
    this.getLines = function(firstRow, lastRow) {
        return this.doc.getLines(firstRow, lastRow);
    };

    /**
     * Returns the number of rows in the document.
     * @returns {Number}
     **/
    this.getLength = function() {
        return this.doc.getLength();
    };

    /**
     * {:Document.getTextRange.desc}
     * @param {Range} range The range to work with
     *
     * @returns {String}
     **/
    this.getTextRange = function(range) {
        return this.doc.getTextRange(range || this.selection.getRange());
    };

    /**
     * Inserts a block of `text` and the indicated `position`.
     * @param {Object} position The position {row, column} to start inserting at
     * @param {String} text A chunk of text to insert
     * @returns {Object} The position of the last line of `text`. If the length of `text` is 0, this function simply returns `position`.
     *
     *
     **/
    this.insert = function(position, text) {
        return this.doc.insert(position, text);
    };

    /**
     * Removes the `range` from the document.
     * @param {Range} range A specified Range to remove
     * @returns {Object} The new `start` property of the range, which contains `startRow` and `startColumn`. If `range` is empty, this function returns the unmodified value of `range.start`.
     *
     * @related Document.remove
     *
     **/
    this.remove = function(range) {
        return this.doc.remove(range);
    };
    
    /**
    * Removes a range of full lines. This method also triggers the `'change'` event.
    * @param {Number} firstRow The first row to be removed
    * @param {Number} lastRow The last row to be removed
    * @returns {[String]} Returns all the removed lines.
    *
    * @related Document.removeFullLines
    *
    **/
    this.removeFullLines = function(firstRow, lastRow){
        return this.doc.removeFullLines(firstRow, lastRow);
    };

    /**
     * Reverts previous changes to your document.
     * @param {Array} deltas An array of previous changes
     * @param {Boolean} dontSelect [If `true`, doesn't select the range of where the change occured]{: #dontSelect}
    *
     *
     * @returns {Range}
    **/
    this.undoChanges = function(deltas, dontSelect) {
        if (!deltas.length)
            return;

        this.$fromUndo = true;
        var lastUndoRange = null;
        for (var i = deltas.length - 1; i != -1; i--) {
            var delta = deltas[i];
            if (delta.group == "doc") {
                this.doc.revertDeltas(delta.deltas);
                lastUndoRange =
                    this.$getUndoSelection(delta.deltas, true, lastUndoRange);
            } else {
                delta.deltas.forEach(function(foldDelta) {
                    this.addFolds(foldDelta.folds);
                }, this);
            }
        }
        this.$fromUndo = false;
        lastUndoRange &&
            this.$undoSelect &&
            !dontSelect &&
            this.selection.setSelectionRange(lastUndoRange);
        return lastUndoRange;
    };

    /**
     * Re-implements a previously undone change to your document.
     * @param {Array} deltas An array of previous changes
     * @param {Boolean} dontSelect {:dontSelect}
     *
    *
     * @returns {Range}
    **/
    this.redoChanges = function(deltas, dontSelect) {
        if (!deltas.length)
            return;

        this.$fromUndo = true;
        var lastUndoRange = null;
        for (var i = 0; i < deltas.length; i++) {
            var delta = deltas[i];
            if (delta.group == "doc") {
                this.doc.applyDeltas(delta.deltas);
                lastUndoRange =
                    this.$getUndoSelection(delta.deltas, false, lastUndoRange);
            }
        }
        this.$fromUndo = false;
        lastUndoRange &&
            this.$undoSelect &&
            !dontSelect &&
            this.selection.setSelectionRange(lastUndoRange);
        return lastUndoRange;
    };

    /**
     * Enables or disables highlighting of the range where an undo occured.
     * @param {Boolean} enable If `true`, selects the range of the reinserted change
    *
    **/
    this.setUndoSelect = function(enable) {
        this.$undoSelect = enable;
    };

    this.$getUndoSelection = function(deltas, isUndo, lastUndoRange) {
        function isInsert(delta) {
            return isUndo ? delta.action !== "insert" : delta.action === "insert";
        }

        var delta = deltas[0];
        var range, point;
        var lastDeltaIsInsert = false;
        if (isInsert(delta)) {
            range = Range.fromPoints(delta.start, delta.end);
            lastDeltaIsInsert = true;
        } else {
            range = Range.fromPoints(delta.start, delta.start);
            lastDeltaIsInsert = false;
        }

        for (var i = 1; i < deltas.length; i++) {
            delta = deltas[i];
            if (isInsert(delta)) {
                point = delta.start;
                if (range.compare(point.row, point.column) == -1) {
                    range.setStart(point);
                }
                point = delta.end;
                if (range.compare(point.row, point.column) == 1) {
                    range.setEnd(point);
                }
                lastDeltaIsInsert = true;
            } else {
                point = delta.start;
                if (range.compare(point.row, point.column) == -1) {
                    range = Range.fromPoints(delta.start, delta.start);
                }
                lastDeltaIsInsert = false;
            }
        }

        // Check if this range and the last undo range has something in common.
        // If true, merge the ranges.
        if (lastUndoRange != null) {
            if (Range.comparePoints(lastUndoRange.start, range.start) === 0) {
                lastUndoRange.start.column += range.end.column - range.start.column;
                lastUndoRange.end.column += range.end.column - range.start.column;
            }

            var cmp = lastUndoRange.compareRange(range);
            if (cmp == 1) {
                range.setStart(lastUndoRange.start);
            } else if (cmp == -1) {
                range.setEnd(lastUndoRange.end);
            }
        }

        return range;
    };

    /**
    * Replaces a range in the document with the new `text`.
    *
    * @param {Range} range A specified Range to replace
    * @param {String} text The new text to use as a replacement
    * @returns {Object} An object containing the final row and column, like this:
    * ```
    * {row: endRow, column: 0}
    * ```
    * If the text and range are empty, this function returns an object containing the current `range.start` value.
    * If the text is the exact same as what currently exists, this function returns an object containing the current `range.end` value.
    *
    *
    *
    * @related Document.replace
    *
    *
    **/
    this.replace = function(range, text) {
        return this.doc.replace(range, text);
    };

    /**
    * Moves a range of text from the given range to the given position. `toPosition` is an object that looks like this:
     *  ```json
    *    { row: newRowLocation, column: newColumnLocation }
     *  ```
     * @param {Range} fromRange The range of text you want moved within the document
     * @param {Object} toPosition The location (row and column) where you want to move the text to
     * @returns {Range} The new range where the text was moved to.
    *
    *
    *
    **/
    this.moveText = function(fromRange, toPosition, copy) {
        var text = this.getTextRange(fromRange);
        var folds = this.getFoldsInRange(fromRange);

        var toRange = Range.fromPoints(toPosition, toPosition);
        if (!copy) {
            this.remove(fromRange);
            var rowDiff = fromRange.start.row - fromRange.end.row;
            var collDiff = rowDiff ? -fromRange.end.column : fromRange.start.column - fromRange.end.column;
            if (collDiff) {
                if (toRange.start.row == fromRange.end.row && toRange.start.column > fromRange.end.column)
                    toRange.start.column += collDiff;
                if (toRange.end.row == fromRange.end.row && toRange.end.column > fromRange.end.column)
                    toRange.end.column += collDiff;
            }
            if (rowDiff && toRange.start.row >= fromRange.end.row) {
                toRange.start.row += rowDiff;
                toRange.end.row += rowDiff;
            }
        }

        toRange.end = this.insert(toRange.start, text);
        if (folds.length) {
            var oldStart = fromRange.start;
            var newStart = toRange.start;
            var rowDiff = newStart.row - oldStart.row;
            var collDiff = newStart.column - oldStart.column;
            this.addFolds(folds.map(function(x) {
                x = x.clone();
                if (x.start.row == oldStart.row)
                    x.start.column += collDiff;
                if (x.end.row == oldStart.row)
                    x.end.column += collDiff;
                x.start.row += rowDiff;
                x.end.row += rowDiff;
                return x;
            }));
        }

        return toRange;
    };

    /**
    * Indents all the rows, from `startRow` to `endRow` (inclusive), by prefixing each row with the token in `indentString`.
    *
    * If `indentString` contains the `'\t'` character, it's replaced by whatever is defined by [[EditSession.getTabString `getTabString()`]].
    * @param {Number} startRow Starting row
    * @param {Number} endRow Ending row
    * @param {String} indentString The indent token
    *
    *
    **/
    this.indentRows = function(startRow, endRow, indentString) {
        indentString = indentString.replace(/\t/g, this.getTabString());
        for (var row=startRow; row<=endRow; row++)
            this.doc.insertInLine({row: row, column: 0}, indentString);
    };

    /**
    * Outdents all the rows defined by the `start` and `end` properties of `range`.
    * @param {Range} range A range of rows
    *
    *
    **/
    this.outdentRows = function (range) {
        var rowRange = range.collapseRows();
        var deleteRange = new Range(0, 0, 0, 0);
        var size = this.getTabSize();

        for (var i = rowRange.start.row; i <= rowRange.end.row; ++i) {
            var line = this.getLine(i);

            deleteRange.start.row = i;
            deleteRange.end.row = i;
            for (var j = 0; j < size; ++j)
                if (line.charAt(j) != ' ')
                    break;
            if (j < size && line.charAt(j) == '\t') {
                deleteRange.start.column = j;
                deleteRange.end.column = j + 1;
            } else {
                deleteRange.start.column = 0;
                deleteRange.end.column = j;
            }
            this.remove(deleteRange);
        }
    };

    this.$moveLines = function(firstRow, lastRow, dir) {
        firstRow = this.getRowFoldStart(firstRow);
        lastRow = this.getRowFoldEnd(lastRow);
        if (dir < 0) {
            var row = this.getRowFoldStart(firstRow + dir);
            if (row < 0) return 0;
            var diff = row-firstRow;
        } else if (dir > 0) {
            var row = this.getRowFoldEnd(lastRow + dir);
            if (row > this.doc.getLength()-1) return 0;
            var diff = row-lastRow;
        } else {
            firstRow = this.$clipRowToDocument(firstRow);
            lastRow = this.$clipRowToDocument(lastRow);
            var diff = lastRow - firstRow + 1;
        }

        var range = new Range(firstRow, 0, lastRow, Number.MAX_VALUE);
        var folds = this.getFoldsInRange(range).map(function(x){
            x = x.clone();
            x.start.row += diff;
            x.end.row += diff;
            return x;
        });
        
        var lines = dir == 0
            ? this.doc.getLines(firstRow, lastRow)
            : this.doc.removeFullLines(firstRow, lastRow);
        this.doc.insertFullLines(firstRow+diff, lines);
        folds.length && this.addFolds(folds);
        return diff;
    };
    /**
    * Shifts all the lines in the document up one, starting from `firstRow` and ending at `lastRow`.
    * @param {Number} firstRow The starting row to move up
    * @param {Number} lastRow The final row to move up
    * @returns {Number} If `firstRow` is less-than or equal to 0, this function returns 0. Otherwise, on success, it returns -1.
    *
    **/
    this.moveLinesUp = function(firstRow, lastRow) {
        return this.$moveLines(firstRow, lastRow, -1);
    };

    /**
    * Shifts all the lines in the document down one, starting from `firstRow` and ending at `lastRow`.
    * @param {Number} firstRow The starting row to move down
    * @param {Number} lastRow The final row to move down
    * @returns {Number} If `firstRow` is less-than or equal to 0, this function returns 0. Otherwise, on success, it returns -1.
    **/
    this.moveLinesDown = function(firstRow, lastRow) {
        return this.$moveLines(firstRow, lastRow, 1);
    };

    /**
    * Duplicates all the text between `firstRow` and `lastRow`.
    * @param {Number} firstRow The starting row to duplicate
    * @param {Number} lastRow The final row to duplicate
    * @returns {Number} Returns the number of new rows added; in other words, `lastRow - firstRow + 1`.
    *
    *
    **/
    this.duplicateLines = function(firstRow, lastRow) {
        return this.$moveLines(firstRow, lastRow, 0);
    };


    this.$clipRowToDocument = function(row) {
        return Math.max(0, Math.min(row, this.doc.getLength()-1));
    };

    this.$clipColumnToRow = function(row, column) {
        if (column < 0)
            return 0;
        return Math.min(this.doc.getLine(row).length, column);
    };


    this.$clipPositionToDocument = function(row, column) {
        column = Math.max(0, column);

        if (row < 0) {
            row = 0;
            column = 0;
        } else {
            var len = this.doc.getLength();
            if (row >= len) {
                row = len - 1;
                column = this.doc.getLine(len-1).length;
            } else {
                column = Math.min(this.doc.getLine(row).length, column);
            }
        }

        return {
            row: row,
            column: column
        };
    };

    this.$clipRangeToDocument = function(range) {
        if (range.start.row < 0) {
            range.start.row = 0;
            range.start.column = 0;
        } else {
            range.start.column = this.$clipColumnToRow(
                range.start.row,
                range.start.column
            );
        }

        var len = this.doc.getLength() - 1;
        if (range.end.row > len) {
            range.end.row = len;
            range.end.column = this.doc.getLine(len).length;
        } else {
            range.end.column = this.$clipColumnToRow(
                range.end.row,
                range.end.column
            );
        }
        return range;
    };

    // WRAPMODE
    this.$wrapLimit = 80;
    this.$useWrapMode = false;
    this.$wrapLimitRange = {
        min : null,
        max : null
    };

    /**
     * Sets whether or not line wrapping is enabled. If `useWrapMode` is different than the current value, the `'changeWrapMode'` event is emitted.
     * @param {Boolean} useWrapMode Enable (or disable) wrap mode
     *
    *
    **/
    this.setUseWrapMode = function(useWrapMode) {
        if (useWrapMode != this.$useWrapMode) {
            this.$useWrapMode = useWrapMode;
            this.$modified = true;
            this.$resetRowCache(0);

            // If wrapMode is activaed, the wrapData array has to be initialized.
            if (useWrapMode) {
                var len = this.getLength();
                this.$wrapData = Array(len);
                this.$updateWrapData(0, len - 1);
            }

            this._signal("changeWrapMode");
        }
    };

    /**
    * Returns `true` if wrap mode is being used; `false` otherwise.
    * @returns {Boolean}
    **/
    this.getUseWrapMode = function() {
        return this.$useWrapMode;
    };

    // Allow the wrap limit to move freely between min and max. Either
    // parameter can be null to allow the wrap limit to be unconstrained
    // in that direction. Or set both parameters to the same number to pin
    // the limit to that value.
    /**
     * Sets the boundaries of wrap. Either value can be `null` to have an unconstrained wrap, or, they can be the same number to pin the limit. If the wrap limits for `min` or `max` are different, this method also emits the `'changeWrapMode'` event.
     * @param {Number} min The minimum wrap value (the left side wrap)
     * @param {Number} max The maximum wrap value (the right side wrap)
     *
    *
    **/
    this.setWrapLimitRange = function(min, max) {
        if (this.$wrapLimitRange.min !== min || this.$wrapLimitRange.max !== max) {
            this.$wrapLimitRange = { min: min, max: max };
            this.$modified = true;
            // This will force a recalculation of the wrap limit
            if (this.$useWrapMode)
                this._signal("changeWrapMode");
        }
    };

    /**
    * This should generally only be called by the renderer when a resize is detected.
    * @param {Number} desiredLimit The new wrap limit
    * @returns {Boolean}
    *
    * @private
    **/
    this.adjustWrapLimit = function(desiredLimit, $printMargin) {
        var limits = this.$wrapLimitRange;
        if (limits.max < 0)
            limits = {min: $printMargin, max: $printMargin};
        var wrapLimit = this.$constrainWrapLimit(desiredLimit, limits.min, limits.max);
        if (wrapLimit != this.$wrapLimit && wrapLimit > 1) {
            this.$wrapLimit = wrapLimit;
            this.$modified = true;
            if (this.$useWrapMode) {
                this.$updateWrapData(0, this.getLength() - 1);
                this.$resetRowCache(0);
                this._signal("changeWrapLimit");
            }
            return true;
        }
        return false;
    };

    this.$constrainWrapLimit = function(wrapLimit, min, max) {
        if (min)
            wrapLimit = Math.max(min, wrapLimit);

        if (max)
            wrapLimit = Math.min(max, wrapLimit);

        return wrapLimit;
    };

    /**
    * Returns the value of wrap limit.
    * @returns {Number} The wrap limit.
    **/
    this.getWrapLimit = function() {
        return this.$wrapLimit;
    };
    
    /**
     * Sets the line length for soft wrap in the editor. Lines will break
     *  at a minimum of the given length minus 20 chars and at a maximum
     *  of the given number of chars.
     * @param {number} limit The maximum line length in chars, for soft wrapping lines.
     */
    this.setWrapLimit = function (limit) {
        this.setWrapLimitRange(limit, limit);
    };
    
    /**
    * Returns an object that defines the minimum and maximum of the wrap limit; it looks something like this:
    *
    *     { min: wrapLimitRange_min, max: wrapLimitRange_max }
    *
    * @returns {Object}
    **/
    this.getWrapLimitRange = function() {
        // Avoid unexpected mutation by returning a copy
        return {
            min : this.$wrapLimitRange.min,
            max : this.$wrapLimitRange.max
        };
    };

    this.$updateInternalDataOnChange = function(delta) {
        var useWrapMode = this.$useWrapMode;
        var action = delta.action;
        var start = delta.start;
        var end = delta.end;
        var firstRow = start.row;
        var lastRow = end.row;
        var len = lastRow - firstRow;
        var removedFolds = null;
        
        this.$updating = true;
        if (len != 0) {
            if (action === "remove") {
                this[useWrapMode ? "$wrapData" : "$rowLengthCache"].splice(firstRow, len);

                var foldLines = this.$foldData;
                removedFolds = this.getFoldsInRange(delta);
                this.removeFolds(removedFolds);

                var foldLine = this.getFoldLine(end.row);
                var idx = 0;
                if (foldLine) {
                    foldLine.addRemoveChars(end.row, end.column, start.column - end.column);
                    foldLine.shiftRow(-len);

                    var foldLineBefore = this.getFoldLine(firstRow);
                    if (foldLineBefore && foldLineBefore !== foldLine) {
                        foldLineBefore.merge(foldLine);
                        foldLine = foldLineBefore;
                    }
                    idx = foldLines.indexOf(foldLine) + 1;
                }

                for (idx; idx < foldLines.length; idx++) {
                    var foldLine = foldLines[idx];
                    if (foldLine.start.row >= end.row) {
                        foldLine.shiftRow(-len);
                    }
                }

                lastRow = firstRow;
            } else {
                var args = Array(len);
                args.unshift(firstRow, 0);
                var arr = useWrapMode ? this.$wrapData : this.$rowLengthCache
                arr.splice.apply(arr, args);

                // If some new line is added inside of a foldLine, then split
                // the fold line up.
                var foldLines = this.$foldData;
                var foldLine = this.getFoldLine(firstRow);
                var idx = 0;
                if (foldLine) {
                    var cmp = foldLine.range.compareInside(start.row, start.column);
                    // Inside of the foldLine range. Need to split stuff up.
                    if (cmp == 0) {
                        foldLine = foldLine.split(start.row, start.column);
                        if (foldLine) {
                            foldLine.shiftRow(len);
                            foldLine.addRemoveChars(lastRow, 0, end.column - start.column);
                        }
                    } else
                    // Infront of the foldLine but same row. Need to shift column.
                    if (cmp == -1) {
                        foldLine.addRemoveChars(firstRow, 0, end.column - start.column);
                        foldLine.shiftRow(len);
                    }
                    // Nothing to do if the insert is after the foldLine.
                    idx = foldLines.indexOf(foldLine) + 1;
                }

                for (idx; idx < foldLines.length; idx++) {
                    var foldLine = foldLines[idx];
                    if (foldLine.start.row >= firstRow) {
                        foldLine.shiftRow(len);
                    }
                }
            }
        } else {
            // Realign folds. E.g. if you add some new chars before a fold, the
            // fold should "move" to the right.
            len = Math.abs(delta.start.column - delta.end.column);
            if (action === "remove") {
                // Get all the folds in the change range and remove them.
                removedFolds = this.getFoldsInRange(delta);
                this.removeFolds(removedFolds);

                len = -len;
            }
            var foldLine = this.getFoldLine(firstRow);
            if (foldLine) {
                foldLine.addRemoveChars(firstRow, start.column, len);
            }
        }

        if (useWrapMode && this.$wrapData.length != this.doc.getLength()) {
            console.error("doc.getLength() and $wrapData.length have to be the same!");
        }
        this.$updating = false;

        if (useWrapMode)
            this.$updateWrapData(firstRow, lastRow);
        else
            this.$updateRowLengthCache(firstRow, lastRow);

        return removedFolds;
    };

    this.$updateRowLengthCache = function(firstRow, lastRow, b) {
        this.$rowLengthCache[firstRow] = null;
        this.$rowLengthCache[lastRow] = null;
    };

    this.$updateWrapData = function(firstRow, lastRow) {
        var lines = this.doc.getAllLines();
        var tabSize = this.getTabSize();
        var wrapData = this.$wrapData;
        var wrapLimit = this.$wrapLimit;
        var tokens;
        var foldLine;

        var row = firstRow;
        lastRow = Math.min(lastRow, lines.length - 1);
        while (row <= lastRow) {
            foldLine = this.getFoldLine(row, foldLine);
            if (!foldLine) {
                tokens = this.$getDisplayTokens(lines[row]);
                wrapData[row] = this.$computeWrapSplits(tokens, wrapLimit, tabSize);
                row ++;
            } else {
                tokens = [];
                foldLine.walk(function(placeholder, row, column, lastColumn) {
                        var walkTokens;
                        if (placeholder != null) {
                            walkTokens = this.$getDisplayTokens(
                                            placeholder, tokens.length);
                            walkTokens[0] = PLACEHOLDER_START;
                            for (var i = 1; i < walkTokens.length; i++) {
                                walkTokens[i] = PLACEHOLDER_BODY;
                            }
                        } else {
                            walkTokens = this.$getDisplayTokens(
                                lines[row].substring(lastColumn, column),
                                tokens.length);
                        }
                        tokens = tokens.concat(walkTokens);
                    }.bind(this),
                    foldLine.end.row,
                    lines[foldLine.end.row].length + 1
                );

                wrapData[foldLine.start.row] = this.$computeWrapSplits(tokens, wrapLimit, tabSize);
                row = foldLine.end.row + 1;
            }
        }
    };

    // "Tokens"
    var CHAR = 1,
        CHAR_EXT = 2,
        PLACEHOLDER_START = 3,
        PLACEHOLDER_BODY =  4,
        PUNCTUATION = 9,
        SPACE = 10,
        TAB = 11,
        TAB_SPACE = 12;


    this.$computeWrapSplits = function(tokens, wrapLimit, tabSize) {
        if (tokens.length == 0) {
            return [];
        }

        var splits = [];
        var displayLength = tokens.length;
        var lastSplit = 0, lastDocSplit = 0;

        var isCode = this.$wrapAsCode;

        var indentedSoftWrap = this.$indentedSoftWrap;
        var maxIndent = wrapLimit <= Math.max(2 * tabSize, 8)
            || indentedSoftWrap === false ? 0 : Math.floor(wrapLimit / 2);

        function getWrapIndent() {
            var indentation = 0;
            if (maxIndent === 0)
                return indentation;
            if (indentedSoftWrap) {
                for (var i = 0; i < tokens.length; i++) {
                    var token = tokens[i];
                    if (token == SPACE)
                        indentation += 1;
                    else if (token == TAB)
                        indentation += tabSize;
                    else if (token == TAB_SPACE)
                        continue;
                    else
                        break;
                }
            }
            if (isCode && indentedSoftWrap !== false)
                indentation += tabSize;
            return Math.min(indentation, maxIndent);
        }
        function addSplit(screenPos) {
            var displayed = tokens.slice(lastSplit, screenPos);

            // The document size is the current size - the extra width for tabs
            // and multipleWidth characters.
            var len = displayed.length;
            displayed.join("").
                // Get all the TAB_SPACEs.
                replace(/12/g, function() {
                    len -= 1;
                }).
                // Get all the CHAR_EXT/multipleWidth characters.
                replace(/2/g, function() {
                    len -= 1;
                });

            if (!splits.length) {
                indent = getWrapIndent();
                splits.indent = indent;
            }
            lastDocSplit += len;
            splits.push(lastDocSplit);
            lastSplit = screenPos;
        }
        var indent = 0;
        while (displayLength - lastSplit > wrapLimit - indent) {
            // This is, where the split should be.
            var split = lastSplit + wrapLimit - indent;

            // If there is a space or tab at this split position, then making
            // a split is simple.
            if (tokens[split - 1] >= SPACE && tokens[split] >= SPACE) {
                /* disabled see https://github.com/ajaxorg/ace/issues/1186
                // Include all following spaces + tabs in this split as well.
                while (tokens[split] >= SPACE) {
                    split ++;
                } */
                addSplit(split);
                continue;
            }

            // === ELSE ===
            // Check if split is inside of a placeholder. Placeholder are
            // not splitable. Therefore, seek the beginning of the placeholder
            // and try to place the split beofre the placeholder's start.
            if (tokens[split] == PLACEHOLDER_START || tokens[split] == PLACEHOLDER_BODY) {
                // Seek the start of the placeholder and do the split
                // before the placeholder. By definition there always
                // a PLACEHOLDER_START between split and lastSplit.
                for (split; split != lastSplit - 1; split--) {
                    if (tokens[split] == PLACEHOLDER_START) {
                        // split++; << No incremental here as we want to
                        //  have the position before the Placeholder.
                        break;
                    }
                }

                // If the PLACEHOLDER_START is not the index of the
                // last split, then we can do the split
                if (split > lastSplit) {
                    addSplit(split);
                    continue;
                }

                // If the PLACEHOLDER_START IS the index of the last
                // split, then we have to place the split after the
                // placeholder. So, let's seek for the end of the placeholder.
                split = lastSplit + wrapLimit;
                for (split; split < tokens.length; split++) {
                    if (tokens[split] != PLACEHOLDER_BODY) {
                        break;
                    }
                }

                // If spilt == tokens.length, then the placeholder is the last
                // thing in the line and adding a new split doesn't make sense.
                if (split == tokens.length) {
                    break;  // Breaks the while-loop.
                }

                // Finally, add the split...
                addSplit(split);
                continue;
            }

            // === ELSE ===
            // Search for the first non space/tab/placeholder/punctuation token backwards.
            var minSplit = Math.max(split - (wrapLimit -(wrapLimit>>2)), lastSplit - 1);
            while (split > minSplit && tokens[split] < PLACEHOLDER_START) {
                split --;
            }
            if (isCode) {
                while (split > minSplit && tokens[split] < PLACEHOLDER_START) {
                    split --;
                }
                while (split > minSplit && tokens[split] == PUNCTUATION) {
                    split --;
                }
            } else {
                while (split > minSplit && tokens[split] < SPACE) {
                    split --;
                }
            }
            // If we found one, then add the split.
            if (split > minSplit) {
                addSplit(++split);
                continue;
            }

            // === ELSE ===
            split = lastSplit + wrapLimit;
            // The split is inside of a CHAR or CHAR_EXT token and no space
            // around -> force a split.
            if (tokens[split] == CHAR_EXT)
                split--;
            addSplit(split - indent);
        }
        return splits;
    };

    /**
    * Given a string, returns an array of the display characters, including tabs and spaces.
    * @param {String} str The string to check
    * @param {Number} offset The value to start at
    *
    *
    **/
    this.$getDisplayTokens = function(str, offset) {
        var arr = [];
        var tabSize;
        offset = offset || 0;

        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            // Tab
            if (c == 9) {
                tabSize = this.getScreenTabSize(arr.length + offset);
                arr.push(TAB);
                for (var n = 1; n < tabSize; n++) {
                    arr.push(TAB_SPACE);
                }
            }
            // Space
            else if (c == 32) {
                arr.push(SPACE);
            } else if((c > 39 && c < 48) || (c > 57 && c < 64)) {
                arr.push(PUNCTUATION);
            }
            // full width characters
            else if (c >= 0x1100 && isFullWidth(c)) {
                arr.push(CHAR, CHAR_EXT);
            } else {
                arr.push(CHAR);
            }
        }
        return arr;
    };

    /**
     * Calculates the width of the string `str` on the screen while assuming that the string starts at the first column on the screen.
    * @param {String} str The string to calculate the screen width of
    * @param {Number} maxScreenColumn
    * @param {Number} screenColumn
    * @returns {[Number]} Returns an `int[]` array with two elements:<br/>
    * The first position indicates the number of columns for `str` on screen.<br/>
    * The second value contains the position of the document column that this function read until.
    *
    **/
    this.$getStringScreenWidth = function(str, maxScreenColumn, screenColumn) {
        if (maxScreenColumn == 0)
            return [0, 0];
        if (maxScreenColumn == null)
            maxScreenColumn = Infinity;
        screenColumn = screenColumn || 0;

        var c, column;
        for (column = 0; column < str.length; column++) {
            c = str.charCodeAt(column);
            // tab
            if (c == 9) {
                screenColumn += this.getScreenTabSize(screenColumn);
            }
            // full width characters
            else if (c >= 0x1100 && isFullWidth(c)) {
                screenColumn += 2;
            } else {
                screenColumn += 1;
            }
            if (screenColumn > maxScreenColumn) {
                break;
            }
        }

        return [screenColumn, column];
    };

    this.lineWidgets = null;
    /**
    * Returns number of screenrows in a wrapped line.
    * @param {Number} row The row number to check
    *
    * @returns {Number}
    **/
    this.getRowLength = function(row) {
        if (this.lineWidgets)
            var h = this.lineWidgets[row] && this.lineWidgets[row].rowCount || 0;
        else 
            h = 0
        if (!this.$useWrapMode || !this.$wrapData[row]) {
            return 1 + h;
        } else {
            return this.$wrapData[row].length + 1 + h;
        }
    };
    this.getRowLineCount = function(row) {
        if (!this.$useWrapMode || !this.$wrapData[row]) {
            return 1;
        } else {
            return this.$wrapData[row].length + 1;
        }
    };

    this.getRowWrapIndent = function(screenRow) {
        if (this.$useWrapMode) {
            var pos = this.screenToDocumentPosition(screenRow, Number.MAX_VALUE);
            var splits = this.$wrapData[pos.row];
            return splits.length && splits[0] < pos.column ? splits.indent : 0;
        } else {
            return 0;
        }
    }

    /**
     * Returns the position (on screen) for the last character in the provided screen row.
     * @param {Number} screenRow The screen row to check
     * @returns {Number}
     *
     * @related EditSession.documentToScreenColumn
    **/
    this.getScreenLastRowColumn = function(screenRow) {
        var pos = this.screenToDocumentPosition(screenRow, Number.MAX_VALUE);
        return this.documentToScreenColumn(pos.row, pos.column);
    };

    /**
    * For the given document row and column, this returns the column position of the last screen row.
    * @param {Number} docRow
    *
    * @param {Number} docColumn
    **/
    this.getDocumentLastRowColumn = function(docRow, docColumn) {
        var screenRow = this.documentToScreenRow(docRow, docColumn);
        return this.getScreenLastRowColumn(screenRow);
    };

    /**
    * For the given document row and column, this returns the document position of the last row.
    * @param {Number} docRow
    * @param {Number} docColumn
    *
    *
    **/
    this.getDocumentLastRowColumnPosition = function(docRow, docColumn) {
        var screenRow = this.documentToScreenRow(docRow, docColumn);
        return this.screenToDocumentPosition(screenRow, Number.MAX_VALUE / 10);
    };

    /**
    * For the given row, this returns the split data.
    * @returns {String}
    **/
    this.getRowSplitData = function(row) {
        if (!this.$useWrapMode) {
            return undefined;
        } else {
            return this.$wrapData[row];
        }
    };

    /**
    * The distance to the next tab stop at the specified screen column.
    * @param {Number} screenColumn The screen column to check
    *
    *
    * @returns {Number}
    **/
    this.getScreenTabSize = function(screenColumn) {
        return this.$tabSize - screenColumn % this.$tabSize;
    };


    this.screenToDocumentRow = function(screenRow, screenColumn) {
        return this.screenToDocumentPosition(screenRow, screenColumn).row;
    };


    this.screenToDocumentColumn = function(screenRow, screenColumn) {
        return this.screenToDocumentPosition(screenRow, screenColumn).column;
    };

    /**
    * Converts characters coordinates on the screen to characters coordinates within the document. [This takes into account code folding, word wrap, tab size, and any other visual modifications.]{: #conversionConsiderations}
    * @param {Number} screenRow The screen row to check
    * @param {Number} screenColumn The screen column to check
    * @returns {Object} The object returned has two properties: `row` and `column`.
    *
    *
    * @related EditSession.documentToScreenPosition
    *
    **/
    this.screenToDocumentPosition = function(screenRow, screenColumn) {
        if (screenRow < 0)
            return {row: 0, column: 0};

        var line;
        var docRow = 0;
        var docColumn = 0;
        var column;
        var row = 0;
        var rowLength = 0;

        var rowCache = this.$screenRowCache;
        var i = this.$getRowCacheIndex(rowCache, screenRow);
        var l = rowCache.length;
        if (l && i >= 0) {
            var row = rowCache[i];
            var docRow = this.$docRowCache[i];
            var doCache = screenRow > rowCache[l - 1];
        } else {
            var doCache = !l;
        }

        var maxRow = this.getLength() - 1;
        var foldLine = this.getNextFoldLine(docRow);
        var foldStart = foldLine ? foldLine.start.row : Infinity;

        while (row <= screenRow) {
            rowLength = this.getRowLength(docRow);
            if (row + rowLength > screenRow || docRow >= maxRow) {
                break;
            } else {
                row += rowLength;
                docRow++;
                if (docRow > foldStart) {
                    docRow = foldLine.end.row+1;
                    foldLine = this.getNextFoldLine(docRow, foldLine);
                    foldStart = foldLine ? foldLine.start.row : Infinity;
                }
            }

            if (doCache) {
                this.$docRowCache.push(docRow);
                this.$screenRowCache.push(row);
            }
        }

        if (foldLine && foldLine.start.row <= docRow) {
            line = this.getFoldDisplayLine(foldLine);
            docRow = foldLine.start.row;
        } else if (row + rowLength <= screenRow || docRow > maxRow) {
            // clip at the end of the document
            return {
                row: maxRow,
                column: this.getLine(maxRow).length
            };
        } else {
            line = this.getLine(docRow);
            foldLine = null;
        }
        var wrapIndent = 0;
        if (this.$useWrapMode) {
            var splits = this.$wrapData[docRow];
            if (splits) {
                var splitIndex = Math.floor(screenRow - row);
                column = splits[splitIndex];
                if(splitIndex > 0 && splits.length) {
                    wrapIndent = splits.indent;
                    docColumn = splits[splitIndex - 1] || splits[splits.length - 1];
                    line = line.substring(docColumn);
                }
            }
        }

        docColumn += this.$getStringScreenWidth(line, screenColumn - wrapIndent)[1];

        // We remove one character at the end so that the docColumn
        // position returned is not associated to the next row on the screen.
        if (this.$useWrapMode && docColumn >= column)
            docColumn = column - 1;

        if (foldLine)
            return foldLine.idxToPosition(docColumn);

        return {row: docRow, column: docColumn};
    };

    /**
    * Converts document coordinates to screen coordinates. {:conversionConsiderations}
    * @param {Number} docRow The document row to check
    * @param {Number} docColumn The document column to check
    * @returns {Object} The object returned by this method has two properties: `row` and `column`.
    *
    *
    * @related EditSession.screenToDocumentPosition
    *
    **/
    this.documentToScreenPosition = function(docRow, docColumn) {
        // Normalize the passed in arguments.
        if (typeof docColumn === "undefined")
            var pos = this.$clipPositionToDocument(docRow.row, docRow.column);
        else
            pos = this.$clipPositionToDocument(docRow, docColumn);

        docRow = pos.row;
        docColumn = pos.column;

        var screenRow = 0;
        var foldStartRow = null;
        var fold = null;

        // Clamp the docRow position in case it's inside of a folded block.
        fold = this.getFoldAt(docRow, docColumn, 1);
        if (fold) {
            docRow = fold.start.row;
            docColumn = fold.start.column;
        }

        var rowEnd, row = 0;


        var rowCache = this.$docRowCache;
        var i = this.$getRowCacheIndex(rowCache, docRow);
        var l = rowCache.length;
        if (l && i >= 0) {
            var row = rowCache[i];
            var screenRow = this.$screenRowCache[i];
            var doCache = docRow > rowCache[l - 1];
        } else {
            var doCache = !l;
        }

        var foldLine = this.getNextFoldLine(row);
        var foldStart = foldLine ?foldLine.start.row :Infinity;

        while (row < docRow) {
            if (row >= foldStart) {
                rowEnd = foldLine.end.row + 1;
                if (rowEnd > docRow)
                    break;
                foldLine = this.getNextFoldLine(rowEnd, foldLine);
                foldStart = foldLine ?foldLine.start.row :Infinity;
            }
            else {
                rowEnd = row + 1;
            }

            screenRow += this.getRowLength(row);
            row = rowEnd;

            if (doCache) {
                this.$docRowCache.push(row);
                this.$screenRowCache.push(screenRow);
            }
        }

        // Calculate the text line that is displayed in docRow on the screen.
        var textLine = "";
        // Check if the final row we want to reach is inside of a fold.
        if (foldLine && row >= foldStart) {
            textLine = this.getFoldDisplayLine(foldLine, docRow, docColumn);
            foldStartRow = foldLine.start.row;
        } else {
            textLine = this.getLine(docRow).substring(0, docColumn);
            foldStartRow = docRow;
        }
        var wrapIndent = 0;
        // Clamp textLine if in wrapMode.
        if (this.$useWrapMode) {
            var wrapRow = this.$wrapData[foldStartRow];
            if (wrapRow) {
                var screenRowOffset = 0;
                while (textLine.length >= wrapRow[screenRowOffset]) {
                    screenRow ++;
                    screenRowOffset++;
                }
                textLine = textLine.substring(
                    wrapRow[screenRowOffset - 1] || 0, textLine.length
                );
                wrapIndent = screenRowOffset > 0 ? wrapRow.indent : 0;
            }
        }

        return {
            row: screenRow,
            column: wrapIndent + this.$getStringScreenWidth(textLine)[0]
        };
    };

    /**
    * For the given document row and column, returns the screen column.
    * @param {Number} row
    * @param {Number} docColumn
    * @returns {Number}
    *
    **/
    this.documentToScreenColumn = function(row, docColumn) {
        return this.documentToScreenPosition(row, docColumn).column;
    };

    /**
    * For the given document row and column, returns the screen row.
    * @param {Number} docRow
    * @param {Number} docColumn
    *
    *
    **/
    this.documentToScreenRow = function(docRow, docColumn) {
        return this.documentToScreenPosition(docRow, docColumn).row;
    };

    /**
    * Returns the length of the screen.
    * @returns {Number}
    **/
    this.getScreenLength = function() {
        var screenRows = 0;
        var fold = null;
        if (!this.$useWrapMode) {
            screenRows = this.getLength();

            // Remove the folded lines again.
            var foldData = this.$foldData;
            for (var i = 0; i < foldData.length; i++) {
                fold = foldData[i];
                screenRows -= fold.end.row - fold.start.row;
            }
        } else {
            var lastRow = this.$wrapData.length;
            var row = 0, i = 0;
            var fold = this.$foldData[i++];
            var foldStart = fold ? fold.start.row :Infinity;

            while (row < lastRow) {
                var splits = this.$wrapData[row];
                screenRows += splits ? splits.length + 1 : 1;
                row ++;
                if (row > foldStart) {
                    row = fold.end.row+1;
                    fold = this.$foldData[i++];
                    foldStart = fold ?fold.start.row :Infinity;
                }
            }
        }

        // todo
        if (this.lineWidgets)
            screenRows += this.$getWidgetScreenLength();

        return screenRows;
    };
    
    /**
     * @private
     *
     */
    this.$setFontMetrics = function(fm) {
        // todo
    };
    
    this.destroy = function() {
        if (this.bgTokenizer) {
            this.bgTokenizer.setDocument(null);
            this.bgTokenizer = null;
        }
        this.$stopWorker();
    };

    // For every keystroke this gets called once per char in the whole doc!!
    // Wouldn't hurt to make it a bit faster for c >= 0x1100
    function isFullWidth(c) {
        if (c < 0x1100)
            return false;
        return c >= 0x1100 && c <= 0x115F ||
               c >= 0x11A3 && c <= 0x11A7 ||
               c >= 0x11FA && c <= 0x11FF ||
               c >= 0x2329 && c <= 0x232A ||
               c >= 0x2E80 && c <= 0x2E99 ||
               c >= 0x2E9B && c <= 0x2EF3 ||
               c >= 0x2F00 && c <= 0x2FD5 ||
               c >= 0x2FF0 && c <= 0x2FFB ||
               c >= 0x3000 && c <= 0x303E ||
               c >= 0x3041 && c <= 0x3096 ||
               c >= 0x3099 && c <= 0x30FF ||
               c >= 0x3105 && c <= 0x312D ||
               c >= 0x3131 && c <= 0x318E ||
               c >= 0x3190 && c <= 0x31BA ||
               c >= 0x31C0 && c <= 0x31E3 ||
               c >= 0x31F0 && c <= 0x321E ||
               c >= 0x3220 && c <= 0x3247 ||
               c >= 0x3250 && c <= 0x32FE ||
               c >= 0x3300 && c <= 0x4DBF ||
               c >= 0x4E00 && c <= 0xA48C ||
               c >= 0xA490 && c <= 0xA4C6 ||
               c >= 0xA960 && c <= 0xA97C ||
               c >= 0xAC00 && c <= 0xD7A3 ||
               c >= 0xD7B0 && c <= 0xD7C6 ||
               c >= 0xD7CB && c <= 0xD7FB ||
               c >= 0xF900 && c <= 0xFAFF ||
               c >= 0xFE10 && c <= 0xFE19 ||
               c >= 0xFE30 && c <= 0xFE52 ||
               c >= 0xFE54 && c <= 0xFE66 ||
               c >= 0xFE68 && c <= 0xFE6B ||
               c >= 0xFF01 && c <= 0xFF60 ||
               c >= 0xFFE0 && c <= 0xFFE6;
    };

}).call(EditSession.prototype);

require("./edit_session/folding").Folding.call(EditSession.prototype);
require("./edit_session/bracket_match").BracketMatch.call(EditSession.prototype);


config.defineOptions(EditSession.prototype, "session", {
    wrap: {
        set: function(value) {
            if (!value || value == "off")
                value = false;
            else if (value == "free")
                value = true;
            else if (value == "printMargin")
                value = -1;
            else if (typeof value == "string")
                value = parseInt(value, 10) || false;

            if (this.$wrap == value)
                return;
            this.$wrap = value;
            if (!value) {
                this.setUseWrapMode(false);
            } else {
                var col = typeof value == "number" ? value : null;
                this.setWrapLimitRange(col, col);
                this.setUseWrapMode(true);
            }
        },
        get: function() {
            if (this.getUseWrapMode()) {
                if (this.$wrap == -1)
                    return "printMargin";
                if (!this.getWrapLimitRange().min)
                    return "free";
                return this.$wrap;
            }
            return "off";
        },
        handlesSet: true
    },    
    wrapMethod: {
        // code|text|auto
        set: function(val) {
            val = val == "auto"
                ? this.$mode.type != "text"
                : val != "text";
            if (val != this.$wrapAsCode) {
                this.$wrapAsCode = val;
                if (this.$useWrapMode) {
                    this.$modified = true;
                    this.$resetRowCache(0);
                    this.$updateWrapData(0, this.getLength() - 1);
                }
            }
        },
        initialValue: "auto"
    },
    indentedSoftWrap: { initialValue: true },
    firstLineNumber: {
        set: function() {this._signal("changeBreakpoint");},
        initialValue: 1
    },
    useWorker: {
        set: function(useWorker) {
            this.$useWorker = useWorker;

            this.$stopWorker();
            if (useWorker)
                this.$startWorker();
        },
        initialValue: true
    },
    useSoftTabs: {initialValue: true},
    tabSize: {
        set: function(tabSize) {
            if (isNaN(tabSize) || this.$tabSize === tabSize) return;

            this.$modified = true;
            this.$rowLengthCache = [];
            this.$tabSize = tabSize;
            this._signal("changeTabSize");
        },
        initialValue: 4,
        handlesSet: true
    },
    overwrite: {
        set: function(val) {this._signal("changeOverwrite");},
        initialValue: false
    },
    newLineMode: {
        set: function(val) {this.doc.setNewLineMode(val)},
        get: function() {return this.doc.getNewLineMode()},
        handlesSet: true
    },
    mode: {
        set: function(val) { this.setMode(val) },
        get: function() { return this.$modeId }
    }
});

exports.EditSession = EditSession;
});
