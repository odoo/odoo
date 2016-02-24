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
var BaseFoldMode = require("./fold_mode").FoldMode;
var Range = require("../../range").Range;

var FoldMode = exports.FoldMode = function() {};
oop.inherits(FoldMode, BaseFoldMode);

(function() {
    this.foldingStartMarker = /^(?:\|={10,}|[\.\/=\-~^+]{4,}\s*$|={1,5} )/;
    this.singleLineHeadingRe = /^={1,5}(?=\s+\S)/;

    this.getFoldWidget = function(session, foldStyle, row) {
        var line = session.getLine(row);
        if (!this.foldingStartMarker.test(line))
            return ""

        if (line[0] == "=") {
            if (this.singleLineHeadingRe.test(line))
                return "start";
            if (session.getLine(row - 1).length != session.getLine(row).length)
                return "";
            return "start";
        }
        if (session.bgTokenizer.getState(row) == "dissallowDelimitedBlock")
            return "end";
        return "start";
    };

    this.getFoldWidgetRange = function(session, foldStyle, row) {
        var line = session.getLine(row);
        var startColumn = line.length;
        var maxRow = session.getLength();
        var startRow = row;
        var endRow = row;
        if (!line.match(this.foldingStartMarker))
            return;

        var token;
        function getTokenType(row) {
            token = session.getTokens(row)[0];
            return token && token.type;
        }

        var levels = ["=","-","~","^","+"];
        var heading = "markup.heading";
        var singleLineHeadingRe = this.singleLineHeadingRe;
        function getLevel() {
            var match = token.value.match(singleLineHeadingRe);
            if (match)
                return match[0].length;
            var level = levels.indexOf(token.value[0]) + 1;
            if (level == 1) {
                if (session.getLine(row - 1).length != session.getLine(row).length)
                    return Infinity;
            }
            return level;
        }

        if (getTokenType(row) == heading) {
            var startHeadingLevel = getLevel();
            while (++row < maxRow) {
                if (getTokenType(row) != heading)
                    continue;
                var level = getLevel();
                if (level <= startHeadingLevel)
                    break;
            }

            var isSingleLineHeading = token && token.value.match(this.singleLineHeadingRe);
            endRow = isSingleLineHeading ? row - 1 : row - 2;

            if (endRow > startRow) {
                while (endRow > startRow && (!getTokenType(endRow) || token.value[0] == "["))
                    endRow--;
            }

            if (endRow > startRow) {
                var endColumn = session.getLine(endRow).length;
                return new Range(startRow, startColumn, endRow, endColumn);
            }
        } else {
            var state = session.bgTokenizer.getState(row);
            if (state == "dissallowDelimitedBlock") {
                while (row -- > 0) {
                    if (session.bgTokenizer.getState(row).lastIndexOf("Block") == -1)
                        break;
                }
                endRow = row + 1;
                if (endRow < startRow) {
                    var endColumn = session.getLine(row).length;
                    return new Range(endRow, 5, startRow, startColumn - 5);
                }
            } else {
                while (++row < maxRow) {
                    if (session.bgTokenizer.getState(row) == "dissallowDelimitedBlock")
                        break;
                }
                endRow = row;
                if (endRow > startRow) {
                    var endColumn = session.getLine(row).length;
                    return new Range(startRow, 5, endRow, endColumn - 5);
                }
            }
        }
    };

}).call(FoldMode.prototype);

});
