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

var TclHighlightRules = function() {

    //TODO var builtinFunctions = "";

    this.$rules = {
        "start" : [
           {
                token : "comment",
                regex : "#.*\\\\$",
                next  : "commentfollow"
            }, {
                token : "comment",
                regex : "#.*$"
            }, {
                token : "support.function",
                regex : '[\\\\]$',
                next  : "splitlineStart"
            }, {
                token : "text",
                regex : '[\\\\](?:["]|[{]|[}]|[[]|[]]|[$]|[\])'
            }, {
                token : "text", // last value before command
                regex : '^|[^{][;][^}]|[/\r/]',
                next  : "commandItem"
            }, {
                token : "string", // single line
                regex : '[ ]*["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
            }, {
                token : "string", // multi line """ string start
                regex : '[ ]*["]',
                next  : "qqstring"
            }, {
                token : "variable.instance",
                regex : "[$]",
                next  : "variable"
            }, {
                token : "support.function",
                regex : "!|\\$|%|&|\\*|\\-\\-|\\-|\\+\\+|\\+|~|===|==|=|!=|!==|<=|>=|<<=|>>=|>>>=|<>|<|>|!|&&|\\|\\||\\?\\:|\\*=|%=|\\+=|\\-=|&=|\\^=|{\\*}|;|::"
            }, {
                token : "identifier",
                regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
            }, {
                token : "paren.lparen",
                regex : "[[{]",
                next  : "commandItem"
            }, {
                token : "paren.lparen",
                regex : "[(]"
            },  {
                token : "paren.rparen",
                regex : "[\\])}]"
            }, {
                token : "text",
                regex : "\\s+"
            }
        ],
        "commandItem" : [
            {
                token : "comment",
                regex : "#.*\\\\$",
                next  : "commentfollow"
            }, {
                token : "comment",
                regex : "#.*$",
                next  : "start"
            }, {
                token : "string", // single line
                regex : '[ ]*["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
            }, {
                token : "variable.instance", 
                regex : "[$]",
                next  : "variable"
            }, {
                token : "support.function",
                regex : "(?:[:][:])[a-zA-Z0-9_/]+(?:[:][:])",
                next  : "commandItem"
            }, {
                token : "support.function",
                regex : "[a-zA-Z0-9_/]+(?:[:][:])",
                next  : "commandItem"
            }, {
                token : "support.function",
                regex : "(?:[:][:])",
                next  : "commandItem"
            }, {
                token : "paren.rparen",
                regex : "[\\])}]"
            }, {
                token : "support.function",
                regex : "!|\\$|%|&|\\*|\\-\\-|\\-|\\+\\+|\\+|~|===|==|=|!=|!==|<=|>=|<<=|>>=|>>>=|<>|<|>|!|&&|\\|\\||\\?\\:|\\*=|%=|\\+=|\\-=|&=|\\^=|{\\*}|;|::"
            }, {
                token : "keyword",
                regex : "[a-zA-Z0-9_/]+",
                next  : "start"
            } ],
        "commentfollow" : [ 
            {
                token : "comment",
                regex : ".*\\\\$",
                next  : "commentfollow"
            }, {
                token : "comment",
                regex : '.+',
                next  : "start"
        } ],
        "splitlineStart" : [ 
            {
                token : "text",
                regex : "^.",
                next  : "start"
            }],
        "variable" : [ 
            {
                token : "variable.instance", // variable tcl
                regex : "[a-zA-Z_\\d]+(?:[(][a-zA-Z_\\d]+[)])?",
                next  : "start"
            }, {
                token : "variable.instance", // variable tcl with braces
                regex : "{?[a-zA-Z_\\d]+}?",
                next  : "start"
            }],  
        "qqstring" : [ {
            token : "string", // multi line """ string end
            regex : '(?:[^\\\\]|\\\\.)*?["]',
            next : "start"
        }, {
            token : "string",
            regex : '.+'
        } ]
    };
};

oop.inherits(TclHighlightRules, TextHighlightRules);

exports.TclHighlightRules = TclHighlightRules;
});
