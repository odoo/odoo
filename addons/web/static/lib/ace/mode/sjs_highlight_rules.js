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
var JavaScriptHighlightRules = require("./javascript_highlight_rules").JavaScriptHighlightRules;
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var SJSHighlightRules = function() {
    var parent = new JavaScriptHighlightRules({noES6: true});
    var escapedRe = "\\\\(?:x[0-9a-fA-F]{2}|" + // hex
        "u[0-9a-fA-F]{4}|" + // unicode
        "[0-2][0-7]{0,2}|" + // oct
        "3[0-6][0-7]?|" + // oct
        "37[0-7]?|" + // oct
        "[4-7][0-7]?|" + //oct
        ".)";

    var contextAware = function(f) {
        f.isContextAware = true;
        return f;
    };

    var ctxBegin = function(opts) {
        return {
            token: opts.token,
            regex: opts.regex,
            next: contextAware(function(currentState, stack) {
                if (stack.length === 0)
                    stack.unshift(currentState);
                stack.unshift(opts.next);
                return opts.next;
            }),
        };
    };

    var ctxEnd = function(opts) {
        return {
            token: opts.token,
            regex: opts.regex,
            next: contextAware(function(currentState, stack) {
                stack.shift();
                return stack[0] || "start";
            }),
        };
    };

    this.$rules = parent.$rules;
    this.$rules.no_regex = [
        {
            token: "keyword",
            regex: "(waitfor|or|and|collapse|spawn|retract)\\b"
        },
        {
            token: "keyword.operator",
            regex: "(->|=>|\\.\\.)"
        },
        {
            token: "variable.language",
            regex: "(hold|default)\\b"
        },
        ctxBegin({
            token: "string",
            regex: "`",
            next: "bstring"
        }),
        ctxBegin({
            token: "string",
            regex: '"',
            next: "qqstring"
        }),
        ctxBegin({
            token: "string",
            regex: '"',
            next: "qqstring"
        }),
        {
            token: ["paren.lparen", "text", "paren.rparen"],
            regex: "(\\{)(\\s*)(\\|)",
            next: "block_arguments",
        }

    ].concat(this.$rules.no_regex);

    this.$rules.block_arguments = [
        {
            token: "paren.rparen",
            regex: "\\|",
            next: "no_regex",
        }
    ].concat(this.$rules.function_arguments);

    this.$rules.bstring = [
        {
            token : "constant.language.escape",
            regex : escapedRe
        },
        {
            token : "string",
            regex : "\\\\$",
            next: "bstring"
        },
        ctxBegin({
            token : "paren.lparen",
            regex : "\\$\\{",
            next: "string_interp"
        }),
        ctxBegin({
            token : "paren.lparen",
            regex : "\\$",
            next: "bstring_interp_single"
        }),
        ctxEnd({
            token : "string",
            regex : "`",
        }),
        {
            defaultToken: "string"
        }
    ];
    
    this.$rules.qqstring = [
        {
            token : "constant.language.escape",
            regex : escapedRe
        },
        {
            token : "string",
            regex : "\\\\$",
            next: "qqstring",
        },
        ctxBegin({
            token : "paren.lparen",
            regex : "#\\{",
            next: "string_interp"
        }),
        ctxEnd({
            token : "string",
            regex : '"',
        }),
        {
            defaultToken: "string"
        }
    ];

    // collect all context-aware (or stateless), brace-less
    // states. This gives us most normal highlighting
    // for use within interpreted contexts
    // without interfering with context nesting
    var embeddableRules = [];
    for (var i=0; i < this.$rules.no_regex.length; i++) {
        var rule = this.$rules.no_regex[i];
        var token = String(rule.token);
        if (token.indexOf('paren') == -1 && (!rule.next || rule.next.isContextAware)) {
            embeddableRules.push(rule);
        }
    };

    this.$rules.string_interp = [
        ctxEnd({
            token: "paren.rparen",
            regex: "\\}"
        }),
        ctxBegin({
            token: "paren.lparen",
            regex: '{',
            next: "string_interp"
        })
    ].concat(embeddableRules);

    // backtick strings can have single interpolation, which accept
    // \w+ followed by an optional set of function call parens
    this.$rules.bstring_interp_single = [
        {
            token: ["identifier", "paren.lparen"],
            regex: '(\\w+)(\\()',
            next: 'bstring_interp_single_call'
        },
        // identifier-only match ends this interp
        ctxEnd({
            token : "identifier",
            regex : "\\w*",
        })
    ];
    
    // the call part of a bstring_interp_single
    // is terminated by a close paren `)`, but
    // can have nested parens.
    this.$rules.bstring_interp_single_call = [
        ctxBegin({
            token: "paren.lparen",
            regex: "\\(",
            next: "bstring_interp_single_call"
        }),
        ctxEnd({
            token: "paren.rparen",
            regex: "\\)"
        })
    ].concat(embeddableRules);
}
oop.inherits(SJSHighlightRules, TextHighlightRules);

exports.SJSHighlightRules = SJSHighlightRules;
});
