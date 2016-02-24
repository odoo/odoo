define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var escape = "\\\\(?:u[\\da-fA-F]{4}|x[\\da-fA-F]{2}|.)";
var quantifier = "({\\d+\\b,?\\d*}|[+*?])(\\??)";

var JsRegexHighlightRules = function() {
    this.$rules = {
        "start": [{
                // operators
                token : "keyword",
                regex: "\\\\[bB]",
                next: "no_quantifier"
            }, {
                token: "regexp.keyword.operator",
                regex: escape
            }, {
                // flag
                token: "string.regexp",
                regex: "/\\w*",
                next: "start"
            }, {               
                token : ["string", "string.regex"],
                regex: quantifier,
                next: "no_quantifier"
            }, {
                // operators
                token : "keyword",
                regex: "[$^]|\\\\[bB]",
                next: "no_quantifier"
            }, {
                // operators
                token : "constant.language.escape",
                regex: /\(\?[:=!]|\)|[()$^+*?]/,
                next: "no_quantifier"
            }, {
                token : "constant.language.delimiter",
                regex: /\|/,
                next: "no_quantifier"
            }, {
                token: "constant.language.escape",
                regex: /\[\^?/,
                next: "character_class"
            }, {
                token: "empty",
                regex: "$",
                next: "start"
            }
        ],
        

        "character_class": [{
                regex: /\\[dDwWsS]/
            },{
                token: "markup.list",
                regex: "(?:" + escape + "|.)-(?:[^\\]\\\\]|" + escape + ")"
            }, {
                token: "keyword",
                regex: escape
            }, {
                token: "constant.language.escape",
                regex: "]",
                next: "start"
            }, {
                token: "constant.language.escape",
                regex: "-"
            }, {
                token: "empty",
                regex: "$",
                next: "start"
            }, {
                defaultToken: "string.regexp.charachterclass"
            }
        ],
        "no_quantifier":[{
                token: "invalid",
                regex: quantifier
            }, {
                token: "invalid",
                regex: "",
                next: "start"
            }
        ]
        
    };
};

oop.inherits(JsRegexHighlightRules, TextHighlightRules);

exports.JsRegexHighlightRules = JsRegexHighlightRules;
});
