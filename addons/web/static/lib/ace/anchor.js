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
var EventEmitter = require("./lib/event_emitter").EventEmitter;

/**
 *
 * Defines a floating pointer in the document. Whenever text is inserted or deleted before the cursor, the position of the anchor is updated.
 *
 * @class Anchor
 **/

/**
 * Creates a new `Anchor` and associates it with a document.
 *
 * @param {Document} doc The document to associate with the anchor
 * @param {Number} row The starting row position
 * @param {Number} column The starting column position
 *
 * @constructor
 **/

var Anchor = exports.Anchor = function(doc, row, column) {
    this.$onChange = this.onChange.bind(this);
    this.attach(doc);
    
    if (typeof column == "undefined")
        this.setPosition(row.row, row.column);
    else
        this.setPosition(row, column);
};

(function() {

    oop.implement(this, EventEmitter);

    /**
     * Returns an object identifying the `row` and `column` position of the current anchor.
     * @returns {Object}
     **/
    this.getPosition = function() {
        return this.$clipPositionToDocument(this.row, this.column);
    };

    /**
     *
     * Returns the current document.
     * @returns {Document}
     **/
    this.getDocument = function() {
        return this.document;
    };

    /**
     * experimental: allows anchor to stick to the next on the left
     */
    this.$insertRight = false;
    /**
     * Fires whenever the anchor position changes.
     *
     * Both of these objects have a `row` and `column` property corresponding to the position.
     *
     * Events that can trigger this function include [[Anchor.setPosition `setPosition()`]].
     *
     * @event change
     * @param {Object} e  An object containing information about the anchor position. It has two properties:
     *  - `old`: An object describing the old Anchor position
     *  - `value`: An object describing the new Anchor position
     *
     **/
    this.onChange = function(delta) {
        if (delta.start.row == delta.end.row && delta.start.row != this.row)
            return;

        if (delta.start.row > this.row)
            return;
            
        var point = $getTransformedPoint(delta, {row: this.row, column: this.column}, this.$insertRight);
        this.setPosition(point.row, point.column, true);
    };
    
    function $pointsInOrder(point1, point2, equalPointsInOrder) {
        var bColIsAfter = equalPointsInOrder ? point1.column <= point2.column : point1.column < point2.column;
        return (point1.row < point2.row) || (point1.row == point2.row && bColIsAfter);
    }
            
    function $getTransformedPoint(delta, point, moveIfEqual) {
        // Get delta info.
        var deltaIsInsert = delta.action == "insert";
        var deltaRowShift = (deltaIsInsert ? 1 : -1) * (delta.end.row    - delta.start.row);
        var deltaColShift = (deltaIsInsert ? 1 : -1) * (delta.end.column - delta.start.column);
        var deltaStart = delta.start;
        var deltaEnd = deltaIsInsert ? deltaStart : delta.end; // Collapse insert range.
        
        // DELTA AFTER POINT: No change needed.
        if ($pointsInOrder(point, deltaStart, moveIfEqual)) {
            return {
                row: point.row,
                column: point.column
            };
        }
        
        // DELTA BEFORE POINT: Move point by delta shift.
        if ($pointsInOrder(deltaEnd, point, !moveIfEqual)) {
            return {
                row: point.row + deltaRowShift,
                column: point.column + (point.row == deltaEnd.row ? deltaColShift : 0)
            };
        }
        
        // DELTA ENVELOPS POINT (delete only): Move point to delta start.
        // TODO warn if delta.action != "remove" ?
        
        return {
            row: deltaStart.row,
            column: deltaStart.column
        };
    }

    /**
     * Sets the anchor position to the specified row and column. If `noClip` is `true`, the position is not clipped.
     * @param {Number} row The row index to move the anchor to
     * @param {Number} column The column index to move the anchor to
     * @param {Boolean} noClip Identifies if you want the position to be clipped
     *
     **/
    this.setPosition = function(row, column, noClip) {
        var pos;
        if (noClip) {
            pos = {
                row: row,
                column: column
            };
        } else {
            pos = this.$clipPositionToDocument(row, column);
        }

        if (this.row == pos.row && this.column == pos.column)
            return;

        var old = {
            row: this.row,
            column: this.column
        };

        this.row = pos.row;
        this.column = pos.column;
        this._signal("change", {
            old: old,
            value: pos
        });
    };

    /**
     * When called, the `"change"` event listener is removed.
     *
     **/
    this.detach = function() {
        this.document.removeEventListener("change", this.$onChange);
    };
    this.attach = function(doc) {
        this.document = doc || this.document;
        this.document.on("change", this.$onChange);
    };

    /**
     * Clips the anchor position to the specified row and column.
     * @param {Number} row The row index to clip the anchor to
     * @param {Number} column The column index to clip the anchor to
     *
     **/
    this.$clipPositionToDocument = function(row, column) {
        var pos = {};

        if (row >= this.document.getLength()) {
            pos.row = Math.max(0, this.document.getLength() - 1);
            pos.column = this.document.getLine(pos.row).length;
        }
        else if (row < 0) {
            pos.row = 0;
            pos.column = 0;
        }
        else {
            pos.row = row;
            pos.column = Math.min(this.document.getLine(pos.row).length, Math.max(0, column));
        }

        if (column < 0)
            pos.column = 0;

        return pos;
    };

}).call(Anchor.prototype);

});
