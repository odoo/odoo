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
var applyDelta = require("./apply_delta").applyDelta;
var EventEmitter = require("./lib/event_emitter").EventEmitter;
var Range = require("./range").Range;
var Anchor = require("./anchor").Anchor;

/**
 * Contains the text of the document. Document can be attached to several [[EditSession `EditSession`]]s. 
 * At its core, `Document`s are just an array of strings, with each row in the document matching up to the array index.
 *
 * @class Document
 **/

/**
 *
 * Creates a new `Document`. If `text` is included, the `Document` contains those strings; otherwise, it's empty.
 * @param {String | Array} text The starting text
 * @constructor
 **/

var Document = function(textOrLines) {
    this.$lines = [""];

    // There has to be one line at least in the document. If you pass an empty
    // string to the insert function, nothing will happen. Workaround.
    if (textOrLines.length === 0) {
        this.$lines = [""];
    } else if (Array.isArray(textOrLines)) {
        this.insertMergedLines({row: 0, column: 0}, textOrLines);
    } else {
        this.insert({row: 0, column:0}, textOrLines);
    }
};

(function() {

    oop.implement(this, EventEmitter);

    /**
    * Replaces all the lines in the current `Document` with the value of `text`.
    *
    * @param {String} text The text to use
    **/
    this.setValue = function(text) {
        var len = this.getLength() - 1;
        this.remove(new Range(0, 0, len, this.getLine(len).length));
        this.insert({row: 0, column: 0}, text);
    };

    /**
    * Returns all the lines in the document as a single string, joined by the new line character.
    **/
    this.getValue = function() {
        return this.getAllLines().join(this.getNewLineCharacter());
    };

    /** 
    * Creates a new `Anchor` to define a floating point in the document.
    * @param {Number} row The row number to use
    * @param {Number} column The column number to use
    *
    **/
    this.createAnchor = function(row, column) {
        return new Anchor(this, row, column);
    };

    /** 
    * Splits a string of text on any newline (`\n`) or carriage-return (`\r`) characters.
    *
    * @method $split
    * @param {String} text The text to work with
    * @returns {String} A String array, with each index containing a piece of the original `text` string.
    *
    **/

    // check for IE split bug
    if ("aaa".split(/a/).length === 0) {
        this.$split = function(text) {
            return text.replace(/\r\n|\r/g, "\n").split("\n");
        };
    } else {
        this.$split = function(text) {
            return text.split(/\r\n|\r|\n/);
        };
    }


    this.$detectNewLine = function(text) {
        var match = text.match(/^.*?(\r\n|\r|\n)/m);
        this.$autoNewLine = match ? match[1] : "\n";
        this._signal("changeNewLineMode");
    };

    /**
    * Returns the newline character that's being used, depending on the value of `newLineMode`. 
    * @returns {String} If `newLineMode == windows`, `\r\n` is returned.  
    *  If `newLineMode == unix`, `\n` is returned.  
    *  If `newLineMode == auto`, the value of `autoNewLine` is returned.
    *
    **/
    this.getNewLineCharacter = function() {
        switch (this.$newLineMode) {
          case "windows":
            return "\r\n";
          case "unix":
            return "\n";
          default:
            return this.$autoNewLine || "\n";
        }
    };

    this.$autoNewLine = "";
    this.$newLineMode = "auto";
    /**
     * [Sets the new line mode.]{: #Document.setNewLineMode.desc}
     * @param {String} newLineMode [The newline mode to use; can be either `windows`, `unix`, or `auto`]{: #Document.setNewLineMode.param}
     *
     **/
    this.setNewLineMode = function(newLineMode) {
        if (this.$newLineMode === newLineMode)
            return;

        this.$newLineMode = newLineMode;
        this._signal("changeNewLineMode");
    };

    /**
    * [Returns the type of newlines being used; either `windows`, `unix`, or `auto`]{: #Document.getNewLineMode}
    * @returns {String}
    **/
    this.getNewLineMode = function() {
        return this.$newLineMode;
    };

    /**
    * Returns `true` if `text` is a newline character (either `\r\n`, `\r`, or `\n`).
    * @param {String} text The text to check
    *
    **/
    this.isNewLine = function(text) {
        return (text == "\r\n" || text == "\r" || text == "\n");
    };

    /**
    * Returns a verbatim copy of the given line as it is in the document
    * @param {Number} row The row index to retrieve
    *
    **/
    this.getLine = function(row) {
        return this.$lines[row] || "";
    };

    /**
    * Returns an array of strings of the rows between `firstRow` and `lastRow`. This function is inclusive of `lastRow`.
    * @param {Number} firstRow The first row index to retrieve
    * @param {Number} lastRow The final row index to retrieve
    *
    **/
    this.getLines = function(firstRow, lastRow) {
        return this.$lines.slice(firstRow, lastRow + 1);
    };

    /**
    * Returns all lines in the document as string array.
    **/
    this.getAllLines = function() {
        return this.getLines(0, this.getLength());
    };

    /**
    * Returns the number of rows in the document.
    **/
    this.getLength = function() {
        return this.$lines.length;
    };

    /**
    * Returns all the text within `range` as a single string.
    * @param {Range} range The range to work with.
    * 
    * @returns {String}
    **/
    this.getTextRange = function(range) {
        return this.getLinesForRange(range).join(this.getNewLineCharacter());
    };
    
    /**
    * Returns all the text within `range` as an array of lines.
    * @param {Range} range The range to work with.
    * 
    * @returns {Array}
    **/
    this.getLinesForRange = function(range) {
        var lines;
        if (range.start.row === range.end.row) {
            // Handle a single-line range.
            lines = [this.getLine(range.start.row).substring(range.start.column, range.end.column)];
        } else {
            // Handle a multi-line range.
            lines = this.getLines(range.start.row, range.end.row);
            lines[0] = (lines[0] || "").substring(range.start.column);
            var l = lines.length - 1;
            if (range.end.row - range.start.row == l)
                lines[l] = lines[l].substring(0, range.end.column);
        }
        return lines;
    };

    // Deprecated methods retained for backwards compatibility.
    this.insertLines = function(row, lines) {
        console.warn("Use of document.insertLines is deprecated. Use the insertFullLines method instead.");
        return this.insertFullLines(row, lines);
    };
    this.removeLines = function(firstRow, lastRow) {
        console.warn("Use of document.removeLines is deprecated. Use the removeFullLines method instead.");
        return this.removeFullLines(firstRow, lastRow);
    };
    this.insertNewLine = function(position) {
        console.warn("Use of document.insertNewLine is deprecated. Use insertMergedLines(position, [\'\', \'\']) instead.");
        return this.insertMergedLines(position, ["", ""]);
    };

    /**
    * Inserts a block of `text` at the indicated `position`.
    * @param {Object} position The position to start inserting at; it's an object that looks like `{ row: row, column: column}`
    * @param {String} text A chunk of text to insert
    * @returns {Object} The position ({row, column}) of the last line of `text`. If the length of `text` is 0, this function simply returns `position`. 
    *
    **/
    this.insert = function(position, text) {
        // Only detect new lines if the document has no line break yet.
        if (this.getLength() <= 1)
            this.$detectNewLine(text);
        
        return this.insertMergedLines(position, this.$split(text));
    };
    
    /**
    * Inserts `text` into the `position` at the current row. This method also triggers the `"change"` event.
    * 
    * This differs from the `insert` method in two ways:
    *   1. This does NOT handle newline characters (single-line text only).
    *   2. This is faster than the `insert` method for single-line text insertions.
    * 
    * @param {Object} position The position to insert at; it's an object that looks like `{ row: row, column: column}`
    * @param {String} text A chunk of text
    * @returns {Object} Returns an object containing the final row and column, like this:  
    *     ```
    *     {row: endRow, column: 0}
    *     ```
    **/
    this.insertInLine = function(position, text) {
        var start = this.clippedPos(position.row, position.column);
        var end = this.pos(position.row, position.column + text.length);
        
        this.applyDelta({
            start: start,
            end: end,
            action: "insert",
            lines: [text]
        }, true);
        
        return this.clonePos(end);
    };
    
    this.clippedPos = function(row, column) {
        var length = this.getLength();
        if (row === undefined) {
            row = length;
        } else if (row < 0) {
            row = 0;
        } else if (row >= length) {
            row = length - 1;
            column = undefined;
        }
        var line = this.getLine(row);
        if (column == undefined)
            column = line.length;
        column = Math.min(Math.max(column, 0), line.length);
        return {row: row, column: column};
    };
    
    this.clonePos = function(pos) {
        return {row: pos.row, column: pos.column};
    };
    
    this.pos = function(row, column) {
        return {row: row, column: column};
    };
    
    this.$clipPosition = function(position) {
        var length = this.getLength();
        if (position.row >= length) {
            position.row = Math.max(0, length - 1);
            position.column = this.getLine(length - 1).length;
        } else {
            position.row = Math.max(0, position.row);
            position.column = Math.min(Math.max(position.column, 0), this.getLine(position.row).length);
        }
        return position;
    };

    /**
    * Fires whenever the document changes.
    *
    * Several methods trigger different `"change"` events. Below is a list of each action type, followed by each property that's also available:
    *
    *  * `"insert"`
    *    * `range`: the [[Range]] of the change within the document
    *    * `lines`: the lines being added
    *  * `"remove"`
    *    * `range`: the [[Range]] of the change within the document
    *    * `lines`: the lines being removed
    *
    * @event change
    * @param {Object} e Contains at least one property called `"action"`. `"action"` indicates the action that triggered the change. Each action also has a set of additional properties.
    *
    **/
    
    /**
    * Inserts the elements in `lines` into the document as full lines (does not merge with existing line), starting at the row index given by `row`. This method also triggers the `"change"` event.
    * @param {Number} row The index of the row to insert at
    * @param {Array} lines An array of strings
    * @returns {Object} Contains the final row and column, like this:  
    *   ```
    *   {row: endRow, column: 0}
    *   ```  
    *   If `lines` is empty, this function returns an object containing the current row, and column, like this:  
    *   ``` 
    *   {row: row, column: 0}
    *   ```
    *
    **/
    this.insertFullLines = function(row, lines) {
        // Clip to document.
        // Allow one past the document end.
        row = Math.min(Math.max(row, 0), this.getLength());
        
        // Calculate insertion point.
        var column = 0;
        if (row < this.getLength()) {
            // Insert before the specified row.
            lines = lines.concat([""]);
            column = 0;
        } else {
            // Insert after the last row in the document.
            lines = [""].concat(lines);
            row--;
            column = this.$lines[row].length;
        }
        
        // Insert.
        this.insertMergedLines({row: row, column: column}, lines);
    };

    /**
    * Inserts the elements in `lines` into the document, starting at the position index given by `row`. This method also triggers the `"change"` event.
    * @param {Number} row The index of the row to insert at
    * @param {Array} lines An array of strings
    * @returns {Object} Contains the final row and column, like this:  
    *   ```
    *   {row: endRow, column: 0}
    *   ```  
    *   If `lines` is empty, this function returns an object containing the current row, and column, like this:  
    *   ``` 
    *   {row: row, column: 0}
    *   ```
    *
    **/    
    this.insertMergedLines = function(position, lines) {
        var start = this.clippedPos(position.row, position.column);
        var end = {
            row: start.row + lines.length - 1,
            column: (lines.length == 1 ? start.column : 0) + lines[lines.length - 1].length
        };
        
        this.applyDelta({
            start: start,
            end: end,
            action: "insert",
            lines: lines
        });
        
        return this.clonePos(end);
    };

    /**
    * Removes the `range` from the document.
    * @param {Range} range A specified Range to remove
    * @returns {Object} Returns the new `start` property of the range, which contains `startRow` and `startColumn`. If `range` is empty, this function returns the unmodified value of `range.start`.
    *
    **/
    this.remove = function(range) {
        var start = this.clippedPos(range.start.row, range.start.column);
        var end = this.clippedPos(range.end.row, range.end.column);
        this.applyDelta({
            start: start,
            end: end,
            action: "remove",
            lines: this.getLinesForRange({start: start, end: end})
        });
        return this.clonePos(start);
    };

    /**
     * Removes the specified columns from the `row`. This method also triggers a `"change"` event.
     * @param {Number} row The row to remove from
     * @param {Number} startColumn The column to start removing at 
     * @param {Number} endColumn The column to stop removing at
     * @returns {Object} Returns an object containing `startRow` and `startColumn`, indicating the new row and column values.<br/>If `startColumn` is equal to `endColumn`, this function returns nothing.
     *
     **/
    this.removeInLine = function(row, startColumn, endColumn) {
        var start = this.clippedPos(row, startColumn);
        var end = this.clippedPos(row, endColumn);
        
        this.applyDelta({
            start: start,
            end: end,
            action: "remove",
            lines: this.getLinesForRange({start: start, end: end})
        }, true);
        
        return this.clonePos(start);
    };

    /**
    * Removes a range of full lines. This method also triggers the `"change"` event.
    * @param {Number} firstRow The first row to be removed
    * @param {Number} lastRow The last row to be removed
    * @returns {[String]} Returns all the removed lines.
    *
    **/
    this.removeFullLines = function(firstRow, lastRow) {
        // Clip to document.
        firstRow = Math.min(Math.max(0, firstRow), this.getLength() - 1);
        lastRow  = Math.min(Math.max(0, lastRow ), this.getLength() - 1);
        
        // Calculate deletion range.
        // Delete the ending new line unless we're at the end of the document.
        // If we're at the end of the document, delete the starting new line.
        var deleteFirstNewLine = lastRow == this.getLength() - 1 && firstRow > 0;
        var deleteLastNewLine  = lastRow  < this.getLength() - 1;
        var startRow = ( deleteFirstNewLine ? firstRow - 1                  : firstRow                    );
        var startCol = ( deleteFirstNewLine ? this.getLine(startRow).length : 0                           );
        var endRow   = ( deleteLastNewLine  ? lastRow + 1                   : lastRow                     );
        var endCol   = ( deleteLastNewLine  ? 0                             : this.getLine(endRow).length ); 
        var range = new Range(startRow, startCol, endRow, endCol);
        
        // Store delelted lines with bounding newlines ommitted (maintains previous behavior).
        var deletedLines = this.$lines.slice(firstRow, lastRow + 1);
        
        this.applyDelta({
            start: range.start,
            end: range.end,
            action: "remove",
            lines: this.getLinesForRange(range)
        });
        
        // Return the deleted lines.
        return deletedLines;
    };

    /**
    * Removes the new line between `row` and the row immediately following it. This method also triggers the `"change"` event.
    * @param {Number} row The row to check
    *
    **/
    this.removeNewLine = function(row) {
        if (row < this.getLength() - 1 && row >= 0) {
            this.applyDelta({
                start: this.pos(row, this.getLine(row).length),
                end: this.pos(row + 1, 0),
                action: "remove",
                lines: ["", ""]
            });
        }
    };

    /**
    * Replaces a range in the document with the new `text`.
    * @param {Range} range A specified Range to replace
    * @param {String} text The new text to use as a replacement
    * @returns {Object} Returns an object containing the final row and column, like this:
    *     {row: endRow, column: 0}
    * If the text and range are empty, this function returns an object containing the current `range.start` value.
    * If the text is the exact same as what currently exists, this function returns an object containing the current `range.end` value.
    *
    **/
    this.replace = function(range, text) {
        if (!range instanceof Range)
            range = Range.fromPoints(range.start, range.end);
        if (text.length === 0 && range.isEmpty())
            return range.start;

        // Shortcut: If the text we want to insert is the same as it is already
        // in the document, we don't have to replace anything.
        if (text == this.getTextRange(range))
            return range.end;

        this.remove(range);
        var end;
        if (text) {
            end = this.insert(range.start, text);
        }
        else {
            end = range.start;
        }
        
        return end;
    };

    /**
    * Applies all changes in `deltas` to the document.
    * @param {Array} deltas An array of delta objects (can include "insert" and "remove" actions)
    **/
    this.applyDeltas = function(deltas) {
        for (var i=0; i<deltas.length; i++) {
            this.applyDelta(deltas[i]);
        }
    };
    
    /**
    * Reverts all changes in `deltas` from the document.
    * @param {Array} deltas An array of delta objects (can include "insert" and "remove" actions)
    **/
    this.revertDeltas = function(deltas) {
        for (var i=deltas.length-1; i>=0; i--) {
            this.revertDelta(deltas[i]);
        }
    };
    
    /**
    * Applies `delta` to the document.
    * @param {Object} delta A delta object (can include "insert" and "remove" actions)
    **/
    this.applyDelta = function(delta, doNotValidate) {
        var isInsert = delta.action == "insert";
        // An empty range is a NOOP.
        if (isInsert ? delta.lines.length <= 1 && !delta.lines[0]
            : !Range.comparePoints(delta.start, delta.end)) {
            return;
        }
        
        if (isInsert && delta.lines.length > 20000)
            this.$splitAndapplyLargeDelta(delta, 20000);
        
        // Apply.
        applyDelta(this.$lines, delta, doNotValidate);
        this._signal("change", delta);
    };
    
    this.$splitAndapplyLargeDelta = function(delta, MAX) {
        // Split large insert deltas. This is necessary because:
        //    1. We need to support splicing delta lines into the document via $lines.splice.apply(...)
        //    2. fn.apply() doesn't work for a large number of params. The smallest threshold is on chrome 40 ~42000.
        // we use 20000 to leave some space for actual stack
        // 
        // To Do: Ideally we'd be consistent and also split 'delete' deltas. We don't do this now, because delete
        //        delta handling is too slow. If we make delete delta handling faster we can split all large deltas
        //        as shown in https://gist.github.com/aldendaniels/8367109#file-document-snippet-js
        //        If we do this, update validateDelta() to limit the number of lines in a delete delta.
        var lines = delta.lines;
        var l = lines.length;
        var row = delta.start.row; 
        var column = delta.start.column;
        var from = 0, to = 0;
        do {
            from = to;
            to += MAX - 1;
            var chunk = lines.slice(from, to);
            if (to > l) {
                // Update remaining delta.
                delta.lines = chunk;
                delta.start.row = row + from;
                delta.start.column = column;
                break;
            }
            chunk.push("");
            this.applyDelta({
                start: this.pos(row + from, column),
                end: this.pos(row + to, column = 0),
                action: delta.action,
                lines: chunk
            }, true);
        } while(true);
    };
    
    /**
    * Reverts `delta` from the document.
    * @param {Object} delta A delta object (can include "insert" and "remove" actions)
    **/
    this.revertDelta = function(delta) {
        this.applyDelta({
            start: this.clonePos(delta.start),
            end: this.clonePos(delta.end),
            action: (delta.action == "insert" ? "remove" : "insert"),
            lines: delta.lines.slice()
        });
    };
    
    /**
     * Converts an index position in a document to a `{row, column}` object.
     *
     * Index refers to the "absolute position" of a character in the document. For example:
     *
     * ```javascript
     * var x = 0; // 10 characters, plus one for newline
     * var y = -1;
     * ```
     * 
     * Here, `y` is an index 15: 11 characters for the first row, and 5 characters until `y` in the second.
     *
     * @param {Number} index An index to convert
     * @param {Number} startRow=0 The row from which to start the conversion
     * @returns {Object} A `{row, column}` object of the `index` position
     */
    this.indexToPosition = function(index, startRow) {
        var lines = this.$lines || this.getAllLines();
        var newlineLength = this.getNewLineCharacter().length;
        for (var i = startRow || 0, l = lines.length; i < l; i++) {
            index -= lines[i].length + newlineLength;
            if (index < 0)
                return {row: i, column: index + lines[i].length + newlineLength};
        }
        return {row: l-1, column: lines[l-1].length};
    };

    /**
     * Converts the `{row, column}` position in a document to the character's index.
     *
     * Index refers to the "absolute position" of a character in the document. For example:
     *
     * ```javascript
     * var x = 0; // 10 characters, plus one for newline
     * var y = -1;
     * ```
     * 
     * Here, `y` is an index 15: 11 characters for the first row, and 5 characters until `y` in the second.
     *
     * @param {Object} pos The `{row, column}` to convert
     * @param {Number} startRow=0 The row from which to start the conversion
     * @returns {Number} The index position in the document
     */
    this.positionToIndex = function(pos, startRow) {
        var lines = this.$lines || this.getAllLines();
        var newlineLength = this.getNewLineCharacter().length;
        var index = 0;
        var row = Math.min(pos.row, lines.length);
        for (var i = startRow || 0; i < row; ++i)
            index += lines[i].length + newlineLength;

        return index + pos.column;
    };

}).call(Document.prototype);

exports.Document = Document;
});
