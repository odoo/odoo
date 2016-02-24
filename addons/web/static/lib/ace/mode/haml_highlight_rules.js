define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
var RubyExports = require("./ruby_highlight_rules");
var RubyHighlightRules = RubyExports.RubyHighlightRules;

var HamlHighlightRules = function() {

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = 
        {
    "start": [
        {
            token : "punctuation.section.comment",
            regex : /^\s*\/.*/
        },
        {
            token : "punctuation.section.comment",
            regex : /^\s*#.*/
        },
        {
            token: "string.quoted.double",
            regex: "==.+?=="
        },
        {
            token: "keyword.other.doctype",
            regex: "^!!!\\s*(?:[a-zA-Z0-9-_]+)?"
        },
        RubyExports.qString,
        RubyExports.qqString,
        RubyExports.tString,
        {
            token: ["entity.name.tag.haml"],
            regex: /^\s*%[\w:]+/,
            next: "tag_single"
        },
        {
            token: [ "meta.escape.haml" ],
            regex: "^\\s*\\\\."
        },
        RubyExports.constantNumericHex,
        RubyExports.constantNumericFloat,
        
        RubyExports.constantOtherSymbol,
        {
            token: "text",
            regex: "=|-|~",
            next: "embedded_ruby"
        }
    ],
    "tag_single": [
        {
            token: "entity.other.attribute-name.class.haml",
            regex: "\\.[\\w-]+"
        },
        {
            token: "entity.other.attribute-name.id.haml",
            regex: "#[\\w-]+"
        },
        {
            token: "punctuation.section",
            regex: "\\{",
            next: "section"
        },
        
        RubyExports.constantOtherSymbol,
        
        {
            token: "text",
            regex: /\s/,
            next: "start"
        },
        {
            token: "empty",
            regex: "$|(?!\\.|#|\\{|\\[|=|-|~|\\/)",
            next: "start"
        }
    ],
    "section": [
        RubyExports.constantOtherSymbol,
        
        RubyExports.qString,
        RubyExports.qqString,
        RubyExports.tString,
        
        RubyExports.constantNumericHex,
        RubyExports.constantNumericFloat,
        {
            token: "punctuation.section",
            regex: "\\}",
            next: "start"
        } 
    ],
    "embedded_ruby": [ 
        RubyExports.constantNumericHex,
        RubyExports.constantNumericFloat,
        {
                token : "support.class", // class name
                regex : "[A-Z][a-zA-Z_\\d]+"
        },    
        {
            token : new RubyHighlightRules().getKeywords(),
            regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
        },
        {
            token : ["keyword", "text", "text"],
            regex : "(?:do|\\{)(?: \\|[^|]+\\|)?$",
            next  : "start"
        }, 
        {
            token : ["text"],
            regex : "^$",
            next  : "start"
        }, 
        {
            token : ["text"],
            regex : "^(?!.*\\|\\s*$)",
            next  : "start"
        }
    ]
}

};

oop.inherits(HamlHighlightRules, TextHighlightRules);

exports.HamlHighlightRules = HamlHighlightRules;
});
