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

var AsciidocHighlightRules = function() {
    var identifierRe = "[a-zA-Z\u00a1-\uffff]+\\b";

    this.$rules = {
        "start": [
            {token: "empty",   regex: /$/},
            {token: "literal", regex: /^\.{4,}\s*$/,  next: "listingBlock"},
            {token: "literal", regex: /^-{4,}\s*$/,   next: "literalBlock"},
            {token: "string",  regex: /^\+{4,}\s*$/,  next: "passthroughBlock"},
            {token: "keyword", regex: /^={4,}\s*$/},
            {token: "text",    regex: /^\s*$/},
            // immediately return to the start mode without matching anything
            {token: "empty", regex: "", next: "dissallowDelimitedBlock"}
        ],

        "dissallowDelimitedBlock": [
            {include: "paragraphEnd"},
            {token: "comment", regex: '^//.+$'},
            {token: "keyword", regex: "^(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION):"},

            {include: "listStart"},
            {token: "literal", regex: /^\s+.+$/, next: "indentedBlock"},
            {token: "empty",   regex: "", next: "text"}
        ],

        "paragraphEnd": [
            {token: "doc.comment", regex: /^\/{4,}\s*$/,    next: "commentBlock"},
            {token: "tableBlock",  regex: /^\s*[|!]=+\s*$/, next: "tableBlock"},
            // open block, ruller
            {token: "keyword",     regex: /^(?:--|''')\s*$/, next: "start"},
            {token: "option",      regex: /^\[.*\]\s*$/,     next: "start"},
            {token: "pageBreak",   regex: /^>{3,}$/,         next: "start"},
            {token: "literal",     regex: /^\.{4,}\s*$/,     next: "listingBlock"},
            {token: "titleUnderline",    regex: /^(?:={2,}|-{2,}|~{2,}|\^{2,}|\+{2,})\s*$/, next: "start"},
            {token: "singleLineTitle",   regex: /^={1,5}\s+\S.*$/, next: "start"},

            {token: "otherBlock",    regex: /^(?:\*{2,}|_{2,})\s*$/, next: "start"},
            // .optional title
            {token: "optionalTitle", regex: /^\.[^.\s].+$/,  next: "start"}
        ],

        "listStart": [
            {token: "keyword",  regex: /^\s*(?:\d+\.|[a-zA-Z]\.|[ixvmIXVM]+\)|\*{1,5}|-|\.{1,5})\s/, next: "listText"},
            {token: "meta.tag", regex: /^.+(?::{2,4}|;;)(?: |$)/, next: "listText"},
            {token: "support.function.list.callout", regex: /^(?:<\d+>|\d+>|>) /, next: "text"},
            // continuation
            {token: "keyword",  regex: /^\+\s*$/, next: "start"}
        ],

        "text": [
            {token: ["link", "variable.language"], regex: /((?:https?:\/\/|ftp:\/\/|file:\/\/|mailto:|callto:)[^\s\[]+)(\[.*?\])/},
            {token: "link", regex: /(?:https?:\/\/|ftp:\/\/|file:\/\/|mailto:|callto:)[^\s\[]+/},
            {token: "link", regex: /\b[\w\.\/\-]+@[\w\.\/\-]+\b/},
            {include: "macros"},
            {include: "paragraphEnd"},
            {token: "literal", regex:/\+{3,}/, next:"smallPassthrough"},
            {token: "escape", regex: /\((?:C|TM|R)\)|\.{3}|->|<-|=>|<=|&#(?:\d+|x[a-fA-F\d]+);|(?: |^)--(?=\s+\S)/},
            {token: "escape", regex: /\\[_*'`+#]|\\{2}[_*'`+#]{2}/},
            {token: "keyword", regex: /\s\+$/},
            // any word
            {token: "text", regex: identifierRe},
            {token: ["keyword", "string", "keyword"],
                regex: /(<<[\w\d\-$]+,)(.*?)(>>|$)/},
            {token: "keyword", regex: /<<[\w\d\-$]+,?|>>/},
            {token: "constant.character", regex: /\({2,3}.*?\){2,3}/},
            // Anchor
            {token: "keyword", regex: /\[\[.+?\]\]/},
            // bibliography
            {token: "support", regex: /^\[{3}[\w\d =\-]+\]{3}/},

            {include: "quotes"},
            // text block end
            {token: "empty", regex: /^\s*$/, next: "start"}
        ],

        "listText": [
            {include: "listStart"},
            {include: "text"}
        ],

        "indentedBlock": [
            {token: "literal", regex: /^[\s\w].+$/, next: "indentedBlock"},
            {token: "literal", regex: "", next: "start"}
        ],

        "listingBlock": [
            {token: "literal", regex: /^\.{4,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "constant.numeric", regex: '<\\d+>'},
            {token: "literal", regex: '[^<]+'},
            {token: "literal", regex: '<'}
        ],
        "literalBlock": [
            {token: "literal", regex: /^-{4,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "constant.numeric", regex: '<\\d+>'},
            {token: "literal", regex: '[^<]+'},
            {token: "literal", regex: '<'}
        ],
        "passthroughBlock": [
            {token: "literal", regex: /^\+{4,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "literal", regex: identifierRe + "|\\d+"},
            {include: "macros"},
            {token: "literal", regex: "."}
        ],

        "smallPassthrough": [
            {token: "literal", regex: /[+]{3,}/, next: "dissallowDelimitedBlock"},
            {token: "literal", regex: /^\s*$/, next: "dissallowDelimitedBlock"},
            {token: "literal", regex: identifierRe + "|\\d+"},
            {include: "macros"}
        ],

        "commentBlock": [
            {token: "doc.comment", regex: /^\/{4,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "doc.comment", regex: '^.*$'}
        ],
        "tableBlock": [
            {token: "tableBlock", regex: /^\s*\|={3,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "tableBlock", regex: /^\s*!={3,}\s*$/, next: "innerTableBlock"},
            {token: "tableBlock", regex: /\|/},
            {include: "text", noEscape: true}
        ],
        "innerTableBlock": [
            {token: "tableBlock", regex: /^\s*!={3,}\s*$/, next: "tableBlock"},
            {token: "tableBlock", regex: /^\s*|={3,}\s*$/, next: "dissallowDelimitedBlock"},
            {token: "tableBlock", regex: /\!/}
        ],
        "macros": [
            {token: "macro", regex: /{[\w\-$]+}/},
            {token: ["text", "string", "text", "constant.character", "text"], regex: /({)([\w\-$]+)(:)?(.+)?(})/},
            {token: ["text", "markup.list.macro", "keyword", "string"], regex: /(\w+)(footnote(?:ref)?::?)([^\s\[]+)?(\[.*?\])?/},
            {token: ["markup.list.macro", "keyword", "string"], regex: /([a-zA-Z\-][\w\.\/\-]*::?)([^\s\[]+)(\[.*?\])?/},
            {token: ["markup.list.macro", "keyword"], regex: /([a-zA-Z\-][\w\.\/\-]+::?)(\[.*?\])/},
            {token: "keyword",     regex: /^:.+?:(?= |$)/}
        ],

        "quotes": [
            {token: "string.italic", regex: /__[^_\s].*?__/},
            {token: "string.italic", regex: quoteRule("_")},
            
            {token: "keyword.bold", regex: /\*\*[^*\s].*?\*\*/},
            {token: "keyword.bold", regex: quoteRule("\\*")},
            
            {token: "literal", regex: quoteRule("\\+")},
            {token: "literal", regex: /\+\+[^+\s].*?\+\+/},
            {token: "literal", regex: /\$\$.+?\$\$/},
            {token: "literal", regex: quoteRule("`")},

            {token: "keyword", regex: quoteRule("^")},
            {token: "keyword", regex: quoteRule("~")},
            {token: "keyword", regex: /##?/},
            {token: "keyword", regex: /(?:\B|^)``|\b''/}
        ]

    };

    function quoteRule(ch) {
        var prefix = /\w/.test(ch) ? "\\b" : "(?:\\B|^)";
        return prefix + ch + "[^" + ch + "].*?" + ch + "(?![\\w*])";
    }

    //addQuoteBlock("text")

    var tokenMap = {
        macro: "constant.character",
        tableBlock: "doc.comment",
        titleUnderline: "markup.heading",
        singleLineTitle: "markup.heading",
        pageBreak: "string",
        option: "string.regexp",
        otherBlock: "markup.list",
        literal: "support.function",
        optionalTitle: "constant.numeric",
        escape: "constant.language.escape",
        link: "markup.underline.list"
    };

    for (var state in this.$rules) {
        var stateRules = this.$rules[state];
        for (var i = stateRules.length; i--; ) {
            var rule = stateRules[i];
            if (rule.include || typeof rule == "string") {
                var args = [i, 1].concat(this.$rules[rule.include || rule]);
                if (rule.noEscape) {
                    args = args.filter(function(x) {
                        return !x.next;
                    });
                }
                stateRules.splice.apply(stateRules, args);
            } else if (rule.token in tokenMap) {
                rule.token = tokenMap[rule.token];
            }
        }
    }
};
oop.inherits(AsciidocHighlightRules, TextHighlightRules);

exports.AsciidocHighlightRules = AsciidocHighlightRules;
});
