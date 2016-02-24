/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2012, Ajax.org B.V.
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

var oop = require("../lib/oop");
var TextMode = require("./text").Mode;
var LogiQLHighlightRules = require("./logiql_highlight_rules").LogiQLHighlightRules;
var FoldMode = require("./folding/coffee").FoldMode;
var TokenIterator = require("../token_iterator").TokenIterator;
var Range = require("../range").Range;
var CstyleBehaviour = require("./behaviour/cstyle").CstyleBehaviour;
var MatchingBraceOutdent = require("./matching_brace_outdent").MatchingBraceOutdent;

var Mode = function() {
    this.HighlightRules = LogiQLHighlightRules;
    this.foldingRules = new FoldMode();
    this.$outdent = new MatchingBraceOutdent();
    this.$behaviour = new CstyleBehaviour();
};
oop.inherits(Mode, TextMode);

(function() {
    this.lineCommentStart = "//";
    this.blockComment = {start: "/*", end: "*/"};

    this.getNextLineIndent = function(state, line, tab) {
        var indent = this.$getIndent(line);

        var tokenizedLine = this.getTokenizer().getLineTokens(line, state);
        var tokens = tokenizedLine.tokens;
        var endState = tokenizedLine.state;
        if (/comment|string/.test(endState))  
            return indent;
        if (tokens.length && tokens[tokens.length - 1].type == "comment.single")
            return indent;

        var match = line.match();
        if (/(-->|<--|<-|->|{)\s*$/.test(line))
            indent += tab;
        return indent;
    };

    this.checkOutdent = function(state, line, input) {
        if (this.$outdent.checkOutdent(line, input))
            return true;

        if (input !== "\n" && input !== "\r\n")
            return false;
            
        if (!/^\s+/.test(line))
            return false;

        return true;
    };

    this.autoOutdent = function(state, doc, row) {
        if (this.$outdent.autoOutdent(doc, row))
            return;
        var prevLine = doc.getLine(row);
        var match = prevLine.match(/^\s+/);
        var column = prevLine.lastIndexOf(".") + 1;
        if (!match || !row || !column) return 0;

        var line = doc.getLine(row + 1);
        var startRange = this.getMatching(doc, {row: row, column: column});
        if (!startRange || startRange.start.row == row) return 0;

        column = match[0].length;
        var indent = this.$getIndent(doc.getLine(startRange.start.row));
        doc.replace(new Range(row + 1, 0, row + 1, column), indent);
    };

    this.getMatching = function(session, row, column) {
        if (row == undefined)
            row = session.selection.lead
        if (typeof row == "object") {
            column = row.column;
            row = row.row;
        }

        var startToken = session.getTokenAt(row, column);
        var KW_START = "keyword.start", KW_END = "keyword.end";
        var tok;
        if (!startToken)
            return;
        if (startToken.type == KW_START) {
            var it = new TokenIterator(session, row, column);
            it.step = it.stepForward;
        } else if (startToken.type == KW_END) {
            var it = new TokenIterator(session, row, column);
            it.step = it.stepBackward;
        } else
            return;

        while (tok = it.step()) {
            if (tok.type == KW_START || tok.type == KW_END)
                break;
        }
        if (!tok || tok.type == startToken.type)
            return;

        var col = it.getCurrentTokenColumn();
        var row = it.getCurrentTokenRow();
        return new Range(row, col, row, col + tok.value.length);
    };
    this.$id = "ace/mode/logiql";
}).call(Mode.prototype);

exports.Mode = Mode;
});