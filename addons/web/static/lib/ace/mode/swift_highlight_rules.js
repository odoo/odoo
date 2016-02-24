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
var lang = require("../lib/lang");
var DocCommentHighlightRules = require("./doc_comment_highlight_rules").DocCommentHighlightRules;
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var SwiftHighlightRules = function() {
   var keywordMapper = this.createKeywordMapper({
        "variable.language": "",
        "keyword": "__COLUMN__|__FILE__|__FUNCTION__|__LINE__"
            + "|as|associativity|break|case|class|continue|default|deinit|didSet"
            + "|do|dynamicType|else|enum|extension|fallthrough|for|func|get|if|import"
            + "|in|infix|init|inout|is|left|let|let|mutating|new|none|nonmutating"
            + "|operator|override|postfix|precedence|prefix|protocol|return|right"
            + "|safe|Self|self|set|struct|subscript|switch|Type|typealias"
            + "|unowned|unsafe|var|weak|where|while|willSet"
            + "|convenience|dynamic|final|infix|lazy|mutating|nonmutating|optional|override|postfix"
            + "|prefix|required|static",
        "storage.type": "bool|double|Double"
            + "|extension|float|Float|int|Int|private|public|string|String",
        "constant.language":
            "false|Infinity|NaN|nil|no|null|null|off|on|super|this|true|undefined|yes",
        "support.function":
            ""
    }, "identifier");
    
    function string(start, options) {
        var nestable = options.nestable || options.interpolation;
        var interpStart = options.interpolation && options.interpolation.nextState || "start";
        var mainRule = {
            regex: start + (options.multiline ? "" : "(?=.)"),
            token: "string.start"
        };
        var nextState = [
            options.escape && {
                regex: options.escape,
                token: "character.escape"
            },
            options.interpolation && {
                token : "paren.quasi.start",
                regex : lang.escapeRegExp(options.interpolation.lead + options.interpolation.open),
                push  : interpStart
            },
            options.error && {
                regex: options.error,
                token: "error.invalid"
            }, 
            {
                regex: start + (options.multiline ? "" : "|$"),
                token: "string.end",
                next: nestable ? "pop" : "start"
            }, {
                defaultToken: "string"
            }
        ].filter(Boolean);
        
        if (nestable)
            mainRule.push = nextState;
        else
            mainRule.next = nextState;
        
        if (!options.interpolation)
            return mainRule;
        
        var open = options.interpolation.open;
        var close = options.interpolation.close;
        var counter = {
            regex: "[" + lang.escapeRegExp(open + close) + "]",
            onMatch: function(val, state, stack) {
                this.next = val == open ? this.nextState : "";
                if (val == open && stack.length) {
                    stack.unshift("start", state);
                    return "paren";
                }
                if (val == close && stack.length) {
                    stack.shift();
                    this.next = stack.shift();
                    if (this.next.indexOf("string") != -1)
                        return "paren.quasi.end";
                }
                return val == open ? "paren.lparen" : "paren.rparen";
            },
            nextState: interpStart
        } 
        return [counter, mainRule];
    }
    
    function comments() {
        return [{
                token : "comment",
                regex : "\\/\\/(?=.)",
                next : [
                    DocCommentHighlightRules.getTagRule(),
                    {token : "comment", regex : "$|^", nextState : "start"},
                    {defaultToken : "comment", caseInsensitive: true}
                ]
            },
            DocCommentHighlightRules.getStartRule("doc-start"),
            {
                token : "comment.start",
                regex : /\/\*/,
                stateName: "nested_comment",
                push : [
                    DocCommentHighlightRules.getTagRule(),
                    {token : "comment.start", regex : /\/\*/, push: "nested_comment"},
                    {token : "comment.end", regex : "\\*\\/", next : "pop"},
                    {defaultToken : "comment", caseInsensitive: true}
                ],
            },
        ];
    }
    

    this.$rules = {
        start: [
            string('"', {
                escape: /\\(?:[0\\tnr"']|u{[a-fA-F1-9]{0,8}})/,
                interpolation: {lead: "\\", open: "(", close: ")"},
                error: /\\./,
                multiline: false
            }),
            comments({type: "c", nestable: true}),
            {
                 regex: /@[a-zA-Z_$][a-zA-Z_$\d\u0080-\ufffe]*/,
                 token: "variable.parameter"
            },
            {
                regex: /[a-zA-Z_$][a-zA-Z_$\d\u0080-\ufffe]*/,
                token: keywordMapper
            },  
            {
                token : "constant.numeric", 
                regex : /[+-]?(?:0(?:b[01]+|o[0-7]+|x[\da-fA-F])|\d+(?:(?:\.\d*)?(?:[PpEe][+-]?\d+)?)\b)/
            }, {
                token : "keyword.operator",
                regex : /--|\+\+|===|==|=|!=|!==|<=|>=|<<=|>>=|>>>=|<>|<|>|!|&&|\|\||\?\:|[!$%&*+\-~\/^]=?/,
                next  : "start"
            }, {
                token : "punctuation.operator",
                regex : /[?:,;.]/,
                next  : "start"
            }, {
                token : "paren.lparen",
                regex : /[\[({]/,
                next  : "start"
            }, {
                token : "paren.rparen",
                regex : /[\])}]/
            }, 
            
        ]
    };
    this.embedRules(DocCommentHighlightRules, "doc-",
        [ DocCommentHighlightRules.getEndRule("start") ]);
    
    this.normalizeRules();
};


oop.inherits(SwiftHighlightRules, TextHighlightRules);

exports.HighlightRules = SwiftHighlightRules;
});