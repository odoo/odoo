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

exports.MaskHighlightRules = MaskHighlightRules;

var oop = require("../lib/oop");
var lang = require("../lib/lang");
var TextRules   = require("./text_highlight_rules").TextHighlightRules;
var JSRules     = require("./javascript_highlight_rules").JavaScriptHighlightRules;
var CssRules    = require("./css_highlight_rules").CssHighlightRules;
var MDRules     = require("./markdown_highlight_rules").MarkdownHighlightRules;
var HTMLRules   = require("./html_highlight_rules").HtmlHighlightRules;

var token_TAG       = "keyword.support.constant.language",
    token_COMPO     = "support.function.markup.bold",
    token_KEYWORD   = "keyword",
    token_LANG      = "constant.language",
    token_UTIL      = "keyword.control.markup.italic",
    token_ATTR      = "support.variable.class",
    token_PUNKT     = "keyword.operator",
    token_ITALIC    = "markup.italic",
    token_BOLD      = "markup.bold",
    token_LPARE     = "paren.lparen",
    token_RPARE     = "paren.rparen";

var const_FUNCTIONS,
    const_KEYWORDS,
    const_CONST,
    const_TAGS;
(function(){
    const_FUNCTIONS = lang.arrayToMap(
        ("log").split("|")
    );
    const_CONST = lang.arrayToMap(
        (":dualbind|:bind|:import|slot|event|style|html|markdown|md").split("|")
    );
    const_KEYWORDS = lang.arrayToMap(
        ("debugger|define|var|if|each|for|of|else|switch|case|with|visible|+if|+each|+for|+switch|+with|+visible|include|import").split("|")
    );
    const_TAGS = lang.arrayToMap(
        ("a|abbr|acronym|address|applet|area|article|aside|audio|b|base|basefont|bdo|" + 
         "big|blockquote|body|br|button|canvas|caption|center|cite|code|col|colgroup|" + 
         "command|datalist|dd|del|details|dfn|dir|div|dl|dt|em|embed|fieldset|" + 
         "figcaption|figure|font|footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|" + 
         "header|hgroup|hr|html|i|iframe|img|input|ins|keygen|kbd|label|legend|li|" + 
         "link|map|mark|menu|meta|meter|nav|noframes|noscript|object|ol|optgroup|" + 
         "option|output|p|param|pre|progress|q|rp|rt|ruby|s|samp|script|section|select|" + 
         "small|source|span|strike|strong|style|sub|summary|sup|table|tbody|td|" + 
         "textarea|tfoot|th|thead|time|title|tr|tt|u|ul|var|video|wbr|xmp").split("|")
    );
}());

function MaskHighlightRules () {

    this.$rules = {
        "start" : [
            Token("comment", "\\/\\/.*$"),
            Token("comment", "\\/\\*", [
                Token("comment", ".*?\\*\\/", "start"),
                Token("comment", ".+")
            ]),
            
            Blocks.string("'''"),
            Blocks.string('"""'),
            Blocks.string('"'),
            Blocks.string("'"),
            
            Blocks.syntax(/(markdown|md)\b/, "md-multiline", "multiline"),
            Blocks.syntax(/html\b/, "html-multiline", "multiline"),
            Blocks.syntax(/(slot|event)\b/, "js-block", "block"),
            Blocks.syntax(/style\b/, "css-block", "block"),
            Blocks.syntax(/var\b/, "js-statement", "attr"),
            
            Blocks.tag(),
            
            Token(token_LPARE, "[[({>]"),
            Token(token_RPARE, "[\\])};]", "start"),
            {
                caseInsensitive: true
            }
        ]
    };
    var rules = this;
    
    addJavaScript("interpolation", /\]/, token_RPARE + "." + token_ITALIC);
    addJavaScript("statement", /\)|}|;/);
    addJavaScript("block", /\}/);
    addCss();
    addMarkdown();
    addHtml();
    
    function addJavaScript(name, escape, closeType) {
        var prfx  =  "js-" + name + "-",
            rootTokens = name === "block" ? ["start"] : ["start", "no_regex"];
        add(
            JSRules
            , prfx
            , escape
            , rootTokens
            , closeType
        );
    }
    function addCss() {
        add(CssRules, "css-block-", /\}/);
    }
    function addMarkdown() {
        add(MDRules, "md-multiline-", /("""|''')/, []);
    }
    function addHtml() {
        add(HTMLRules, "html-multiline-", /("""|''')/);
    }
    function add(Rules, strPrfx, rgxEnd, rootTokens, closeType) {
        var next = "pop";
        var tokens = rootTokens || [ "start" ];
        if (tokens.length === 0) {
            tokens = null;
        }
        if (/block|multiline/.test(strPrfx)) {
            next = strPrfx + "end";
            rules.$rules[next] = [
                Token("empty", "", "start")
            ];
        }
        rules.embedRules(
            Rules
            , strPrfx
            , [ Token(closeType || token_RPARE, rgxEnd, next) ]
            , tokens
            , tokens == null ? true : false
        );
    }

    this.normalizeRules();
}
oop.inherits(MaskHighlightRules, TextRules);

var Blocks = {
    string: function(str, next){
        var token = Token(
            "string.start"
            , str
            , [
                Token(token_LPARE + "." + token_ITALIC, /~\[/, Blocks.interpolation()),
                Token("string.end", str, "pop"),
                {
                    defaultToken: "string"
                }
            ]
            , next
        );
        if (str.length === 1){
            var escaped = Token("string.escape", "\\\\" + str);
            token.push.unshift(escaped);
        }
        return token;
    },
    interpolation: function(){
        return [
            Token(token_UTIL, /\s*\w*\s*:/),
            "js-interpolation-start"
        ];
    },
    tagHead: function (rgx) {
      return Token(token_ATTR, rgx, [
            Token(token_ATTR, /[\w\-_]+/),
            Token(token_LPARE + "." + token_ITALIC, /~\[/, Blocks.interpolation()),
            Blocks.goUp()
        ]);
    },
    tag: function () {
        return {
            token: 'tag',
            onMatch :  function(value) {
                if (void 0 !== const_KEYWORDS[value])
                    return token_KEYWORD;
                if (void 0 !== const_CONST[value])
                    return token_LANG;
                if (void 0 !== const_FUNCTIONS[value])
                    return "support.function";
                if (void 0 !== const_TAGS[value.toLowerCase()])
                    return token_TAG;
                
                return token_COMPO;
            },
            regex : /([@\w\-_:+]+)|((^|\s)(?=\s*(\.|#)))/,
            push: [
                Blocks.tagHead(/\./) ,
                Blocks.tagHead(/\#/) ,
                Blocks.expression(),
                Blocks.attribute(),
                
                Token(token_LPARE, /[;>{]/, "pop")
            ]
        };
    },
    syntax: function(rgx, next, type){
        return {
            token: token_LANG,
            regex : rgx,
            push: ({
                "attr": [
                    next + "-start",
                    Token(token_PUNKT, /;/, "start")
                ],
                "multiline": [
                    Blocks.tagHead(/\./) ,
                    Blocks.tagHead(/\#/) ,
                    Blocks.attribute(),
                    Blocks.expression(),
                    Token(token_LPARE, /[>\{]/),
                    Token(token_PUNKT, /;/, "start"),
                    Token(token_LPARE, /'''|"""/, [ next + "-start" ])
                ],
                "block": [
                    Blocks.tagHead(/\./) ,
                    Blocks.tagHead(/\#/) ,
                    Blocks.attribute(),
                    Blocks.expression(),
                    Token(token_LPARE, /\{/, [ next + "-start" ])
                ]
            })[type]
        };
    },
    attribute: function(){
        return Token(function(value){
            return  /^x\-/.test(value)
                ? token_ATTR + "." + token_BOLD
                : token_ATTR;
        }, /[\w_-]+/, [
            Token(token_PUNKT, /\s*=\s*/, [
                Blocks.string('"'),
                Blocks.string("'"),
                Blocks.word(),
                Blocks.goUp()
            ]),
            Blocks.goUp()
        ]);
    },
    expression: function(){
        return Token(token_LPARE, /\(/, [ "js-statement-start" ]);
    },
    word: function(){
        return Token("string", /[\w-_]+/);
    },
    goUp: function(){
        return Token("text", "", "pop");
    },
    goStart: function(){
        return Token("text", "", "start");
    }
};


function Token(token, rgx, mix) {
    var push, next, onMatch;
    if (arguments.length === 4) {
        push = mix;
        next = arguments[3];
    }
    else if (typeof mix === "string") {
        next = mix;
    }
    else {
        push = mix;
    }
    if (typeof token === "function") {
        onMatch = token;
        token   = "empty";
    }
    return {
        token: token,
        regex: rgx,
        push: push,
        next: next,
        onMatch: onMatch
    };
}

});
