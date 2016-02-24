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

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var JsonHighlightRules = function() {

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used
    this.$rules = {
        "start" : [
            {
                token : "variable", // single line
                regex : '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]\\s*(?=:)'
            }, {
                token : "string", // single line
                regex : '"',
                next  : "string"
            }, {
                token : "constant.numeric", // hex
                regex : "0[xX][0-9a-fA-F]+\\b"
            }, {
                token : "constant.numeric", // float
                regex : "[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?\\b"
            }, {
                token : "constant.language.boolean",
                regex : "(?:true|false)\\b"
            }, {
                token : "invalid.illegal", // single quoted strings are not allowed
                regex : "['](?:(?:\\\\.)|(?:[^'\\\\]))*?[']"
            }, {
                token : "invalid.illegal", // comments are not allowed
                regex : "\\/\\/.*$"
            }, {
                token : "paren.lparen",
                regex : "[[({]"
            }, {
                token : "paren.rparen",
                regex : "[\\])}]"
            }, {
                token : "text",
                regex : "\\s+"
            }
        ],
        "string" : [
            {
                token : "constant.language.escape",
                regex : /\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|["\\\/bfnrt])/
            }, {
                token : "string",
                regex : '[^"\\\\]+'
            }, {
                token : "string",
                regex : '"',
                next  : "start"
            }, {
                token : "string",
                regex : "",
                next  : "start"
            }
        ]
    };
    
};

oop.inherits(JsonHighlightRules, TextHighlightRules);

exports.JsonHighlightRules = JsonHighlightRules;
});
