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

// TODO check with https://github.com/deadfoxygrandpa/Elm.tmLanguage

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var ElmHighlightRules = function() {
    var keywordMapper = this.createKeywordMapper({
       "keyword": "as|case|class|data|default|deriving|do|else|export|foreign|" +
            "hiding|jsevent|if|import|in|infix|infixl|infixr|instance|let|" +
            "module|newtype|of|open|then|type|where|_|port|\u03BB"
    }, "identifier");
    
    var escapeRe = /\\(\d+|['"\\&trnbvf])/;
    
    var smallRe = /[a-z_]/.source;
    var largeRe = /[A-Z]/.source;
    var idRe = /[a-z_A-Z0-9\']/.source;

    this.$rules = {
        start: [{
            token: "string.start",
            regex: '"',
            next: "string"
        }, {
            token: "string.character",
            regex: "'(?:" + escapeRe.source + "|.)'?"
        }, {
            regex: /0(?:[xX][0-9A-Fa-f]+|[oO][0-7]+)|\d+(\.\d+)?([eE][-+]?\d*)?/,
            token: "constant.numeric"
        }, {
            token: "comment",
            regex: "--.*"
        }, {
            token : "keyword",
            regex : /\.\.|\||:|=|\\|\"|->|<-|\u2192/
        }, {
            token : "keyword.operator",
            regex : /[-!#$%&*+.\/<=>?@\\^|~:\u03BB\u2192]+/
        }, {
            token : "operator.punctuation",
            regex : /[,;`]/
        }, {
            regex : largeRe + idRe + "+\\.?",
            token : function(value) {
                if (value[value.length - 1] == ".")
                    return "entity.name.function"; 
                return "constant.language"; 
            }
        }, {
            regex : "^" + smallRe  + idRe + "+",
            token : function(value) {
                return "constant.language"; 
            }
        }, {
            token : keywordMapper,
            regex : "[\\w\\xff-\\u218e\\u2455-\\uffff]+\\b"
        }, {
            regex: "{-#?",
            token: "comment.start",
            onMatch: function(value, currentState, stack) {
                this.next = value.length == 2 ? "blockComment" : "docComment";
                return this.token;
            }
        }, {
            token: "variable.language",
            regex: /\[markdown\|/,
            next: "markdown"
        }, {
            token: "paren.lparen",
            regex: /[\[({]/ 
        }, {
            token: "paren.rparen",
            regex: /[\])}]/
        }, ],
        markdown: [{
            regex: /\|\]/,
            next: "start"
        }, {
            defaultToken : "string"
        }],
        blockComment: [{
            regex: "{-",
            token: "comment.start",
            push: "blockComment"
        }, {
            regex: "-}",
            token: "comment.end",
            next: "pop"
        }, {
            defaultToken: "comment"
        }],
        docComment: [{
            regex: "{-",
            token: "comment.start",
            push: "docComment"
        }, {
            regex: "-}",
            token: "comment.end",
            next: "pop" 
        }, {
            defaultToken: "doc.comment"
        }],
        string: [{
            token: "constant.language.escape",
            regex: escapeRe,
        }, {
            token: "text",
            regex: /\\(\s|$)/,
            next: "stringGap"
        }, {
            token: "string.end",
            regex: '"',
            next: "start"
        }],
        stringGap: [{
            token: "text",
            regex: /\\/,
            next: "string"
        }, {
            token: "error",
            regex: "",
            next: "start"
        }],
    };
    
    this.normalizeRules();
};

oop.inherits(ElmHighlightRules, TextHighlightRules);

exports.ElmHighlightRules = ElmHighlightRules;
});
