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

var oop = require("../../lib/oop");
var Range = require("../../range").Range;
var BaseFoldMode = require("./cstyle").FoldMode;

var FoldMode = exports.FoldMode = function() {};

oop.inherits(FoldMode, BaseFoldMode);

(function() {
    /** 
     * Inheriting cstyle folding because it handles the region comment folding 
     * and special block comment folding appropriately.
     * 
     * Cstyle's getCommentRegionBlock() contains the sql comment characters '--' for end region block.
     */
    
    this.foldingStartMarker = /(\bCASE\b|\bBEGIN\b)|^\s*(\/\*)/i;
    // this.foldingStopMarker = /(\bEND\b)|^[\s\*]*(\*\/)/i;
    this.startRegionRe = /^\s*(\/\*|--)#?region\b/;
    
    this.getFoldWidgetRange = function(session, foldStyle, row, forceMultiline) {
        var line = session.getLine(row);
    
        if (this.startRegionRe.test(line)) return this.getCommentRegionBlock(session, line, row);
    
        var match = line.match(this.foldingStartMarker);
        if (match) {
            var i = match.index;
            if (match[1]) return this.getBeginEndBlock(session, row, i, match[1]);
    
            var range = session.getCommentFoldRange(row, i + match[0].length, 1);
            if (range && !range.isMultiLine()) {
                if (forceMultiline) {
                    range = this.getSectionRange(session, row);
                }
                else if (foldStyle != "all") range = null;
            }
    
            return range;
        }
    
        if (foldStyle === "markbegin") return;
        //TODO: add support for end folding markers
        return;
    };
    
    /**
     * @returns {range} folding block for sequence that starts with 'CASE' or 'BEGIN' and ends with 'END'
     * @param {string} matchSequence - the sequence of charaters that started the fold widget, which should remain visible when the fold widget is folded
     */
    this.getBeginEndBlock = function(session, row, column, matchSequence) {
        var start = {
            row: row,
            column: column + matchSequence.length
        };
        var maxRow = session.getLength();
        var line;
    
        var depth = 1;
        var re = /(\bCASE\b|\bBEGIN\b)|(\bEND\b)/i;
        while (++row < maxRow) {
            line = session.getLine(row);
            var m = re.exec(line);
            if (!m) continue;
            if (m[1]) depth++;
            else depth--;
    
            if (!depth) break;
        }
        var endRow = row;
        if (endRow > start.row) {
            return new Range(start.row, start.column, endRow, line.length);
        }
    };

}).call(FoldMode.prototype);

});
