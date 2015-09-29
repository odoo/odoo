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
var comparePoints = function(p1, p2) {
    return p1.row - p2.row || p1.column - p2.column;
};
/**
 * This object is used in various places to indicate a region within the editor. To better visualize how this works, imagine a rectangle. Each quadrant of the rectangle is analogus to a range, as ranges contain a starting row and starting column, and an ending row, and ending column.
 * @class Range
 **/

/**
 * Creates a new `Range` object with the given starting and ending row and column points.
 * @param {Number} startRow The starting row
 * @param {Number} startColumn The starting column
 * @param {Number} endRow The ending row
 * @param {Number} endColumn The ending column
 *
 * @constructor
 **/
var Range = function(startRow, startColumn, endRow, endColumn) {
    this.start = {
        row: startRow,
        column: startColumn
    };

    this.end = {
        row: endRow,
        column: endColumn
    };
};

(function() {
    /**
     * Returns `true` if and only if the starting row and column, and ending row and column, are equivalent to those given by `range`.
     * @param {Range} range A range to check against
     *
     * @return {Boolean}
     **/
    this.isEqual = function(range) {
        return this.start.row === range.start.row &&
            this.end.row === range.end.row &&
            this.start.column === range.start.column &&
            this.end.column === range.end.column;
    };

    /**
     *
     * Returns a string containing the range's row and column information, given like this:
     * ```
     *    [start.row/start.column] -> [end.row/end.column]
     * ```
     * @return {String}
     **/
    this.toString = function() {
        return ("Range: [" + this.start.row + "/" + this.start.column +
            "] -> [" + this.end.row + "/" + this.end.column + "]");
    };

    /**
     *
     * Returns `true` if the `row` and `column` provided are within the given range. This can better be expressed as returning `true` if:
     * ```javascript
     *    this.start.row <= row <= this.end.row &&
     *    this.start.column <= column <= this.end.column
     * ```
     * @param {Number} row A row to check for
     * @param {Number} column A column to check for
     * @returns {Boolean}
     * @related Range.compare
     **/

    this.contains = function(row, column) {
        return this.compare(row, column) == 0;
    };

    /**
     * Compares `this` range (A) with another range (B).
     * @param {Range} range A range to compare with
     *
     * @related Range.compare
     * @returns {Number} This method returns one of the following numbers:<br/>
     * <br/>
     * * `-2`: (B) is in front of (A), and doesn't intersect with (A)<br/>
     * * `-1`: (B) begins before (A) but ends inside of (A)<br/>
     * * `0`: (B) is completely inside of (A) OR (A) is completely inside of (B)<br/>
     * * `+1`: (B) begins inside of (A) but ends outside of (A)<br/>
     * * `+2`: (B) is after (A) and doesn't intersect with (A)<br/>
     * * `42`: FTW state: (B) ends in (A) but starts outside of (A)
     **/
    this.compareRange = function(range) {
        var cmp,
            end = range.end,
            start = range.start;

        cmp = this.compare(end.row, end.column);
        if (cmp == 1) {
            cmp = this.compare(start.row, start.column);
            if (cmp == 1) {
                return 2;
            } else if (cmp == 0) {
                return 1;
            } else {
                return 0;
            }
        } else if (cmp == -1) {
            return -2;
        } else {
            cmp = this.compare(start.row, start.column);
            if (cmp == -1) {
                return -1;
            } else if (cmp == 1) {
                return 42;
            } else {
                return 0;
            }
        }
    };

    /**
     * Checks the row and column points of `p` with the row and column points of the calling range.
     *
     * @param {Range} p A point to compare with
     *
     * @related Range.compare
     * @returns {Number} This method returns one of the following numbers:<br/>
     * * `0` if the two points are exactly equal<br/>
     * * `-1` if `p.row` is less then the calling range<br/>
     * * `1` if `p.row` is greater than the calling range<br/>
     * <br/>
     * If the starting row of the calling range is equal to `p.row`, and:<br/>
     * * `p.column` is greater than or equal to the calling range's starting column, this returns `0`<br/>
     * * Otherwise, it returns -1<br/>
     *<br/>
     * If the ending row of the calling range is equal to `p.row`, and:<br/>
     * * `p.column` is less than or equal to the calling range's ending column, this returns `0`<br/>
     * * Otherwise, it returns 1<br/>
     **/
    this.comparePoint = function(p) {
        return this.compare(p.row, p.column);
    };

    /**
     * Checks the start and end points of `range` and compares them to the calling range. Returns `true` if the `range` is contained within the caller's range.
     * @param {Range} range A range to compare with
     *
     * @returns {Boolean}
     * @related Range.comparePoint
     **/
    this.containsRange = function(range) {
        return this.comparePoint(range.start) == 0 && this.comparePoint(range.end) == 0;
    };

    /**
     * Returns `true` if passed in `range` intersects with the one calling this method.
     * @param {Range} range A range to compare with
     *
     * @returns {Boolean}
     **/
    this.intersects = function(range) {
        var cmp = this.compareRange(range);
        return (cmp == -1 || cmp == 0 || cmp == 1);
    };

    /**
     * Returns `true` if the caller's ending row point is the same as `row`, and if the caller's ending column is the same as `column`.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     * @returns {Boolean}
     **/
    this.isEnd = function(row, column) {
        return this.end.row == row && this.end.column == column;
    };

    /**
     * Returns `true` if the caller's starting row point is the same as `row`, and if the caller's starting column is the same as `column`.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     * @returns {Boolean}
     **/
    this.isStart = function(row, column) {
        return this.start.row == row && this.start.column == column;
    };

    /**
     * Sets the starting row and column for the range.
     * @param {Number} row A row point to set
     * @param {Number} column A column point to set
     *
     **/
    this.setStart = function(row, column) {
        if (typeof row == "object") {
            this.start.column = row.column;
            this.start.row = row.row;
        } else {
            this.start.row = row;
            this.start.column = column;
        }
    };

    /**
     * Sets the starting row and column for the range.
     * @param {Number} row A row point to set
     * @param {Number} column A column point to set
     *
     **/
    this.setEnd = function(row, column) {
        if (typeof row == "object") {
            this.end.column = row.column;
            this.end.row = row.row;
        } else {
            this.end.row = row;
            this.end.column = column;
        }
    };

    /**
     * Returns `true` if the `row` and `column` are within the given range.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     *
     * @returns {Boolean}
     * @related Range.compare
     **/
    this.inside = function(row, column) {
        if (this.compare(row, column) == 0) {
            if (this.isEnd(row, column) || this.isStart(row, column)) {
                return false;
            } else {
                return true;
            }
        }
        return false;
    };

    /**
     * Returns `true` if the `row` and `column` are within the given range's starting points.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     * @returns {Boolean}
     * @related Range.compare
     **/
    this.insideStart = function(row, column) {
        if (this.compare(row, column) == 0) {
            if (this.isEnd(row, column)) {
                return false;
            } else {
                return true;
            }
        }
        return false;
    };

    /**
     * Returns `true` if the `row` and `column` are within the given range's ending points.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     * @returns {Boolean}
     * @related Range.compare
     *
     **/
    this.insideEnd = function(row, column) {
        if (this.compare(row, column) == 0) {
            if (this.isStart(row, column)) {
                return false;
            } else {
                return true;
            }
        }
        return false;
    };

    /**
     * Checks the row and column points with the row and column points of the calling range.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     *
     * @returns {Number} This method returns one of the following numbers:<br/>
     * `0` if the two points are exactly equal <br/>
     * `-1` if `p.row` is less then the calling range <br/>
     * `1` if `p.row` is greater than the calling range <br/>
     *  <br/>
     * If the starting row of the calling range is equal to `p.row`, and: <br/>
     * `p.column` is greater than or equal to the calling range's starting column, this returns `0`<br/>
     * Otherwise, it returns -1<br/>
     * <br/>
     * If the ending row of the calling range is equal to `p.row`, and: <br/>
     * `p.column` is less than or equal to the calling range's ending column, this returns `0` <br/>
     * Otherwise, it returns 1
     **/
    this.compare = function(row, column) {
        if (!this.isMultiLine()) {
            if (row === this.start.row) {
                return column < this.start.column ? -1 : (column > this.end.column ? 1 : 0);
            };
        }

        if (row < this.start.row)
            return -1;

        if (row > this.end.row)
            return 1;

        if (this.start.row === row)
            return column >= this.start.column ? 0 : -1;

        if (this.end.row === row)
            return column <= this.end.column ? 0 : 1;

        return 0;
    };

    /**
     * Checks the row and column points with the row and column points of the calling range.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     * @returns {Number} This method returns one of the following numbers:<br/>
     * <br/>
     * `0` if the two points are exactly equal<br/>
     * `-1` if `p.row` is less then the calling range<br/>
     * `1` if `p.row` is greater than the calling range, or if `isStart` is `true`.<br/>
     * <br/>
     * If the starting row of the calling range is equal to `p.row`, and:<br/>
     * `p.column` is greater than or equal to the calling range's starting column, this returns `0`<br/>
     * Otherwise, it returns -1<br/>
     * <br/>
     * If the ending row of the calling range is equal to `p.row`, and:<br/>
     * `p.column` is less than or equal to the calling range's ending column, this returns `0`<br/>
     * Otherwise, it returns 1
     *
     **/
    this.compareStart = function(row, column) {
        if (this.start.row == row && this.start.column == column) {
            return -1;
        } else {
            return this.compare(row, column);
        }
    };

    /**
     * Checks the row and column points with the row and column points of the calling range.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     *
     * @returns {Number} This method returns one of the following numbers:<br/>
     * `0` if the two points are exactly equal<br/>
     * `-1` if `p.row` is less then the calling range<br/>
     * `1` if `p.row` is greater than the calling range, or if `isEnd` is `true.<br/>
     * <br/>
     * If the starting row of the calling range is equal to `p.row`, and:<br/>
     * `p.column` is greater than or equal to the calling range's starting column, this returns `0`<br/>
     * Otherwise, it returns -1<br/>
     *<br/>
     * If the ending row of the calling range is equal to `p.row`, and:<br/>
     * `p.column` is less than or equal to the calling range's ending column, this returns `0`<br/>
     * Otherwise, it returns 1
     */
    this.compareEnd = function(row, column) {
        if (this.end.row == row && this.end.column == column) {
            return 1;
        } else {
            return this.compare(row, column);
        }
    };

    /**
     * Checks the row and column points with the row and column points of the calling range.
     * @param {Number} row A row point to compare with
     * @param {Number} column A column point to compare with
     *
     *
     * @returns {Number} This method returns one of the following numbers:<br/>
     * * `1` if the ending row of the calling range is equal to `row`, and the ending column of the calling range is equal to `column`<br/>
     * * `-1` if the starting row of the calling range is equal to `row`, and the starting column of the calling range is equal to `column`<br/>
     * <br/>
     * Otherwise, it returns the value after calling [[Range.compare `compare()`]].
     *
     **/
    this.compareInside = function(row, column) {
        if (this.end.row == row && this.end.column == column) {
            return 1;
        } else if (this.start.row == row && this.start.column == column) {
            return -1;
        } else {
            return this.compare(row, column);
        }
    };

    /**
     * Returns the part of the current `Range` that occurs within the boundaries of `firstRow` and `lastRow` as a new `Range` object.
     * @param {Number} firstRow The starting row
     * @param {Number} lastRow The ending row
     *
     *
     * @returns {Range}
    **/
    this.clipRows = function(firstRow, lastRow) {
        if (this.end.row > lastRow)
            var end = {row: lastRow + 1, column: 0};
        else if (this.end.row < firstRow)
            var end = {row: firstRow, column: 0};

        if (this.start.row > lastRow)
            var start = {row: lastRow + 1, column: 0};
        else if (this.start.row < firstRow)
            var start = {row: firstRow, column: 0};

        return Range.fromPoints(start || this.start, end || this.end);
    };

    /**
     * Changes the row and column points for the calling range for both the starting and ending points.
     * @param {Number} row A new row to extend to
     * @param {Number} column A new column to extend to
     *
     *
     * @returns {Range} The original range with the new row
    **/
    this.extend = function(row, column) {
        var cmp = this.compare(row, column);

        if (cmp == 0)
            return this;
        else if (cmp == -1)
            var start = {row: row, column: column};
        else
            var end = {row: row, column: column};

        return Range.fromPoints(start || this.start, end || this.end);
    };

    this.isEmpty = function() {
        return (this.start.row === this.end.row && this.start.column === this.end.column);
    };

    /**
     *
     * Returns `true` if the range spans across multiple lines.
     * @returns {Boolean}
    **/
    this.isMultiLine = function() {
        return (this.start.row !== this.end.row);
    };

    /**
     *
     * Returns a duplicate of the calling range.
     * @returns {Range}
    **/
    this.clone = function() {
        return Range.fromPoints(this.start, this.end);
    };

    /**
     *
     * Returns a range containing the starting and ending rows of the original range, but with a column value of `0`.
     * @returns {Range}
    **/
    this.collapseRows = function() {
        if (this.end.column == 0)
            return new Range(this.start.row, 0, Math.max(this.start.row, this.end.row-1), 0)
        else
            return new Range(this.start.row, 0, this.end.row, 0)
    };

    /**
     * Given the current `Range`, this function converts those starting and ending points into screen positions, and then returns a new `Range` object.
     * @param {EditSession} session The `EditSession` to retrieve coordinates from
     *
     *
     * @returns {Range}
    **/
    this.toScreenRange = function(session) {
        var screenPosStart = session.documentToScreenPosition(this.start);
        var screenPosEnd = session.documentToScreenPosition(this.end);

        return new Range(
            screenPosStart.row, screenPosStart.column,
            screenPosEnd.row, screenPosEnd.column
        );
    };
    
    
    /* experimental */
    this.moveBy = function(row, column) {
        this.start.row += row;
        this.start.column += column;
        this.end.row += row;
        this.end.column += column;
    };

}).call(Range.prototype);

/**
 * Creates and returns a new `Range` based on the row and column of the given parameters.
 * @param {Range} start A starting point to use
 * @param {Range} end An ending point to use
 *
 * @returns {Range}
**/
Range.fromPoints = function(start, end) {
    return new Range(start.row, start.column, end.row, end.column);
};
Range.comparePoints = comparePoints;

Range.comparePoints = function(p1, p2) {
    return p1.row - p2.row || p1.column - p2.column;
};


exports.Range = Range;
});
