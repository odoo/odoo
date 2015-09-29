/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2014, Ajax.org B.V.
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
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var EiffelHighlightRules = function() {
    var keywords = "across|agent|alias|all|attached|as|assign|attribute|check|" +
        "class|convert|create|debug|deferred|detachable|do|else|elseif|end|" +
        "ensure|expanded|export|external|feature|from|frozen|if|inherit|" +
        "inspect|invariant|like|local|loop|not|note|obsolete|old|once|" +
        "Precursor|redefine|rename|require|rescue|retry|select|separate|" +
        "some|then|undefine|until|variant|when";

    var operatorKeywords = "and|implies|or|xor";

    var languageConstants = "Void";

    var booleanConstants = "True|False";

    var languageVariables = "Current|Result";

    var keywordMapper = this.createKeywordMapper({
        "constant.language": languageConstants,
        "constant.language.boolean": booleanConstants,
        "variable.language": languageVariables,
        "keyword.operator": operatorKeywords,
        "keyword": keywords
    }, "identifier", true);

    var simpleString = /(?:[^"%\b\f\v]|%[A-DFHLNQR-V%'"()<>]|%\/(?:0[xX][\da-fA-F](?:_*[\da-fA-F])*|0[cC][0-7](?:_*[0-7])*|0[bB][01](?:_*[01])*|\d(?:_*\d)*)\/)+?/;

    this.$rules = {
        "start": [{
                token : "string.quoted.other", // Aligned-verbatim-strings (verbatim option not supported)
                regex : /"\[/,
                next: "aligned_verbatim_string"
            }, {
                token : "string.quoted.other", // Non-aligned-verbatim-strings (verbatim option not supported)
                regex : /"\{/,
                next: "non-aligned_verbatim_string"
            }, {
                token : "string.quoted.double",
                regex : /"(?:[^%\b\f\n\r\v]|%[A-DFHLNQR-V%'"()<>]|%\/(?:0[xX][\da-fA-F](?:_*[\da-fA-F])*|0[cC][0-7](?:_*[0-7])*|0[bB][01](?:_*[01])*|\d(?:_*\d)*)\/)*?"/
            }, {
                token : "comment.line.double-dash",
                regex : /--.*/
            }, {
                token : "constant.character",
                regex : /'(?:[^%\b\f\n\r\t\v]|%[A-DFHLNQR-V%'"()<>]|%\/(?:0[xX][\da-fA-F](?:_*[\da-fA-F])*|0[cC][0-7](?:_*[0-7])*|0[bB][01](?:_*[01])*|\d(?:_*\d)*)\/)'/
            }, {
                token : "constant.numeric", // hexa | octal | bin
                regex : /\b0(?:[xX][\da-fA-F](?:_*[\da-fA-F])*|[cC][0-7](?:_*[0-7])*|[bB][01](?:_*[01])*)\b/
            }, {
                token : "constant.numeric",
                regex : /(?:\d(?:_*\d)*)?\.(?:(?:\d(?:_*\d)*)?[eE][+-]?)?\d(?:_*\d)*|\d(?:_*\d)*\.?/
            }, {
                token : "paren.lparen",
                regex : /[\[({]|<<|\|\(/
            }, {
                token : "paren.rparen",
                regex : /[\])}]|>>|\|\)/
            }, {
                token : "keyword.operator", // punctuation
                regex : /:=|->|\.(?=\w)|[;,:?]/
            }, {
                token : "keyword.operator",
                regex : /\\\\|\|\.\.\||\.\.|\/[~\/]?|[><\/]=?|[-+*^=~]/
            }, {
                token : function (v) {
                    var result = keywordMapper (v);
                    if (result === "identifier" && v === v.toUpperCase ()) {
                        result =  "entity.name.type";
                    }
                    return result;
                },
                regex : /[a-zA-Z][a-zA-Z\d_]*\b/
            }, {
                token : "text",
                regex : /\s+/
            }
        ],
        "aligned_verbatim_string" : [{
                token : "string",
                regex : /]"/,
                next : "start"
            }, {
                token : "string",
                regex : simpleString
            }
        ],
        "non-aligned_verbatim_string" : [{
                token : "string.quoted.other",
                regex : /}"/,
                next : "start"
            }, {
                token : "string.quoted.other",
                regex : simpleString
            }
        ]};
};

oop.inherits(EiffelHighlightRules, TextHighlightRules);

exports.EiffelHighlightRules = EiffelHighlightRules;
});
