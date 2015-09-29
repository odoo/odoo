define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var lang = require("../lib/lang");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
var HtmlHighlightRules = require("./html_highlight_rules").HtmlHighlightRules;

var VelocityHighlightRules = function() {
    HtmlHighlightRules.call(this);

    var builtinConstants = lang.arrayToMap(
        ('true|false|null').split('|')
    );

    var builtinFunctions = lang.arrayToMap(
        ("_DateTool|_DisplayTool|_EscapeTool|_FieldTool|_MathTool|_NumberTool|_SerializerTool|_SortTool|_StringTool|_XPathTool").split('|')
    );

    var builtinVariables = lang.arrayToMap(
        ('$contentRoot|$foreach').split('|')
    );

    var keywords = lang.arrayToMap(
        ("#set|#macro|#include|#parse|" +
        "#if|#elseif|#else|#foreach|" +
        "#break|#end|#stop"
        ).split('|')
    );

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules.start.push(
        {
            token : "comment",
            regex : "##.*$"
        },{
            token : "comment.block", // multi line comment
            regex : "#\\*",
            next : "vm_comment"
        }, {
            token : "string.regexp",
            regex : "[/](?:(?:\\[(?:\\\\]|[^\\]])+\\])|(?:\\\\/|[^\\]/]))*[/]\\w*\\s*(?=[).,;]|$)"
        }, {
            token : "string", // single line
            regex : '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
        }, {
            token : "string", // single line
            regex : "['](?:(?:\\\\.)|(?:[^'\\\\]))*?[']"
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
            token : function(value) {
                if (keywords.hasOwnProperty(value))
                    return "keyword";
                else if (builtinConstants.hasOwnProperty(value))
                    return "constant.language";
                else if (builtinVariables.hasOwnProperty(value))
                    return "variable.language";
                else if (builtinFunctions.hasOwnProperty(value) || builtinFunctions.hasOwnProperty(value.substring(1)))
                    return "support.function";
                else if (value == "debugger")
                    return "invalid.deprecated";
                else
                    if(value.match(/^(\$[a-zA-Z_][a-zA-Z0-9_]*)$/))
                        return "variable";
                    return "identifier";
            },
            // TODO: Unicode escape sequences
            // TODO: Unicode identifiers
            regex : "[a-zA-Z$#][a-zA-Z0-9_]*\\b"
        }, {
            token : "keyword.operator",
            regex : "!|&|\\*|\\-|\\+|=|!=|<=|>=|<|>|&&|\\|\\|"
        }, {
            token : "lparen",
            regex : "[[({]"
        }, {
            token : "rparen",
            regex : "[\\])}]"
        }, {
            token : "text",
            regex : "\\s+"
        }
    );

    this.$rules["vm_comment"] = [
        {
            token : "comment", // closing comment
            regex : "\\*#|-->",
            next : "start"
        }, {
            defaultToken: "comment"
        }
    ];

    this.$rules["vm_start"] = [
        {
            token: "variable",
            regex: "}",
            next: "pop"
        }, {
            token : "string.regexp",
            regex : "[/](?:(?:\\[(?:\\\\]|[^\\]])+\\])|(?:\\\\/|[^\\]/]))*[/]\\w*\\s*(?=[).,;]|$)"
        }, {
            token : "string", // single line
            regex : '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
        }, {
            token : "string", // single line
            regex : "['](?:(?:\\\\.)|(?:[^'\\\\]))*?[']"
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
            token : function(value) {
                if (keywords.hasOwnProperty(value))
                    return "keyword";
                else if (builtinConstants.hasOwnProperty(value))
                    return "constant.language";
                else if (builtinVariables.hasOwnProperty(value))
                    return "variable.language";
                else if (builtinFunctions.hasOwnProperty(value) || builtinFunctions.hasOwnProperty(value.substring(1)))
                    return "support.function";
                else if (value == "debugger")
                    return "invalid.deprecated";
                else
                    if(value.match(/^(\$[a-zA-Z_$][a-zA-Z0-9_]*)$/))
                        return "variable";
                    return "identifier";
            },
            // TODO: Unicode escape sequences
            // TODO: Unicode identifiers
            regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
        }, {
            token : "keyword.operator",
            regex : "!|&|\\*|\\-|\\+|=|!=|<=|>=|<|>|&&|\\|\\|"
        }, {
            token : "lparen",
            regex : "[[({]"
        }, {
            token : "rparen",
            regex : "[\\])}]"
        }, {
            token : "text",
            regex : "\\s+"
        }
    ];

    for (var i in this.$rules) {
        this.$rules[i].unshift({
            token: "variable",
            regex: "\\${",
            push: "vm_start"
        });
    }

    this.normalizeRules();
};

oop.inherits(VelocityHighlightRules, TextHighlightRules);

exports.VelocityHighlightRules = VelocityHighlightRules;
});