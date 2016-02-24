define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var ShHighlightFile = require("./sh_highlight_rules");

var MakefileHighlightRules = function() {

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    var keywordMapper = this.createKeywordMapper({
        "keyword": ShHighlightFile.reservedKeywords,
        "support.function.builtin": ShHighlightFile.languageConstructs,
        "invalid.deprecated": "debugger"
    }, "string");

    this.$rules = 
        {
    "start": [
        {
            token: "string.interpolated.backtick.makefile",
            regex: "`",
            next: "shell-start"
        },
        {
            token: "punctuation.definition.comment.makefile",
            regex: /#(?=.)/,
            next: "comment"
        },
        {
            token: [ "keyword.control.makefile"],
            regex: "^(?:\\s*\\b)(\\-??include|ifeq|ifneq|ifdef|ifndef|else|endif|vpath|export|unexport|define|endef|override)(?:\\b)"
        },
        {// ^([^\t ]+(\s[^\t ]+)*:(?!\=))\s*.*
            token: ["entity.name.function.makefile", "text"],
            regex: "^([^\\t ]+(?:\\s[^\\t ]+)*:)(\\s*.*)"
        }
    ],
    "comment": [
        {
            token : "punctuation.definition.comment.makefile",
            regex : /.+\\/
        },
        {
            token : "punctuation.definition.comment.makefile",
            regex : ".+",
            next  : "start"
        }
    ],
    "shell-start": [
        {
            token: keywordMapper,
            regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
        }, 
        {
            token: "string",
            regex : "\\w+"
        }, 
        {
            token : "string.interpolated.backtick.makefile",
            regex : "`",
            next  : "start"
        }
    ]
}

};

oop.inherits(MakefileHighlightRules, TextHighlightRules);

exports.MakefileHighlightRules = MakefileHighlightRules;
});
