define("ace/mode/python_highlight_rules",["require","exports","module","ace/lib/oop","ace/mode/text_highlight_rules"], function(require, exports, module){/*
 * TODO: python delimiters
 */
"use strict";
var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
var PythonHighlightRules = function () {
    var keywords = ("and|as|assert|break|class|continue|def|del|elif|else|except|exec|" +
        "finally|for|from|global|if|import|in|is|lambda|not|or|pass|print|" +
        "raise|return|try|while|with|yield|async|await|nonlocal");
    var builtinConstants = ("True|False|None|NotImplemented|Ellipsis|__debug__");
    var builtinFunctions = ("abs|divmod|input|open|staticmethod|all|enumerate|int|ord|str|any|" +
        "eval|isinstance|pow|sum|basestring|execfile|issubclass|print|super|" +
        "binfile|bin|iter|property|tuple|bool|filter|len|range|type|bytearray|" +
        "float|list|raw_input|unichr|callable|format|locals|reduce|unicode|" +
        "chr|frozenset|long|reload|vars|classmethod|getattr|map|repr|xrange|" +
        "cmp|globals|max|reversed|zip|compile|hasattr|memoryview|round|" +
        "__import__|complex|hash|min|apply|delattr|help|next|setattr|set|" +
        "buffer|dict|hex|object|slice|coerce|dir|id|oct|sorted|intern|" +
        "ascii|breakpoint|bytes");
    var keywordMapper = this.createKeywordMapper({
        "invalid.deprecated": "debugger",
        "support.function": builtinFunctions,
        "variable.language": "self|cls",
        "constant.language": builtinConstants,
        "keyword": keywords
    }, "identifier");
    var strPre = "[uU]?";
    var strRawPre = "[rR]";
    var strFormatPre = "[fF]";
    var strRawFormatPre = "(?:[rR][fF]|[fF][rR])";
    var decimalInteger = "(?:(?:[1-9]\\d*)|(?:0))";
    var octInteger = "(?:0[oO]?[0-7]+)";
    var hexInteger = "(?:0[xX][\\dA-Fa-f]+)";
    var binInteger = "(?:0[bB][01]+)";
    var integer = "(?:" + decimalInteger + "|" + octInteger + "|" + hexInteger + "|" + binInteger + ")";
    var exponent = "(?:[eE][+-]?\\d+)";
    var fraction = "(?:\\.\\d+)";
    var intPart = "(?:\\d+)";
    var pointFloat = "(?:(?:" + intPart + "?" + fraction + ")|(?:" + intPart + "\\.))";
    var exponentFloat = "(?:(?:" + pointFloat + "|" + intPart + ")" + exponent + ")";
    var floatNumber = "(?:" + exponentFloat + "|" + pointFloat + ")";
    var stringEscape = "\\\\(x[0-9A-Fa-f]{2}|[0-7]{3}|[\\\\abfnrtv'\"]|U[0-9A-Fa-f]{8}|u[0-9A-Fa-f]{4})";
    this.$rules = {
        "start": [{
                token: "comment",
                regex: "#.*$"
            }, {
                token: "string", // multi line """ string start
                regex: strPre + '"{3}',
                next: "qqstring3"
            }, {
                token: "string", // " string
                regex: strPre + '"(?=.)',
                next: "qqstring"
            }, {
                token: "string", // multi line ''' string start
                regex: strPre + "'{3}",
                next: "qstring3"
            }, {
                token: "string", // ' string
                regex: strPre + "'(?=.)",
                next: "qstring"
            }, {
                token: "string",
                regex: strRawPre + '"{3}',
                next: "rawqqstring3"
            }, {
                token: "string",
                regex: strRawPre + '"(?=.)',
                next: "rawqqstring"
            }, {
                token: "string",
                regex: strRawPre + "'{3}",
                next: "rawqstring3"
            }, {
                token: "string",
                regex: strRawPre + "'(?=.)",
                next: "rawqstring"
            }, {
                token: "string",
                regex: strFormatPre + '"{3}',
                next: "fqqstring3"
            }, {
                token: "string",
                regex: strFormatPre + '"(?=.)',
                next: "fqqstring"
            }, {
                token: "string",
                regex: strFormatPre + "'{3}",
                next: "fqstring3"
            }, {
                token: "string",
                regex: strFormatPre + "'(?=.)",
                next: "fqstring"
            }, {
                token: "string",
                regex: strRawFormatPre + '"{3}',
                next: "rfqqstring3"
            }, {
                token: "string",
                regex: strRawFormatPre + '"(?=.)',
                next: "rfqqstring"
            }, {
                token: "string",
                regex: strRawFormatPre + "'{3}",
                next: "rfqstring3"
            }, {
                token: "string",
                regex: strRawFormatPre + "'(?=.)",
                next: "rfqstring"
            }, {
                token: "keyword.operator",
                regex: "\\+|\\-|\\*|\\*\\*|\\/|\\/\\/|%|@|<<|>>|&|\\||\\^|~|<|>|<=|=>|==|!=|<>|="
            }, {
                token: "punctuation",
                regex: ",|:|;|\\->|\\+=|\\-=|\\*=|\\/=|\\/\\/=|%=|@=|&=|\\|=|^=|>>=|<<=|\\*\\*="
            }, {
                token: "paren.lparen",
                regex: "[\\[\\(\\{]"
            }, {
                token: "paren.rparen",
                regex: "[\\]\\)\\}]"
            }, {
                token: ["keyword", "text", "entity.name.function"],
                regex: "(def|class)(\\s+)([\\u00BF-\\u1FFF\\u2C00-\\uD7FF\\w]+)"
            }, {
                token: "text",
                regex: "\\s+"
            }, {
                include: "constants"
            }],
        "qqstring3": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string", // multi line """ string end
                regex: '"{3}',
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "qstring3": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string", // multi line ''' string end
                regex: "'{3}",
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "qqstring": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string",
                regex: "\\\\$",
                next: "qqstring"
            }, {
                token: "string",
                regex: '"|$',
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "qstring": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string",
                regex: "\\\\$",
                next: "qstring"
            }, {
                token: "string",
                regex: "'|$",
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "rawqqstring3": [{
                token: "string", // multi line """ string end
                regex: '"{3}',
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "rawqstring3": [{
                token: "string", // multi line ''' string end
                regex: "'{3}",
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "rawqqstring": [{
                token: "string",
                regex: "\\\\$",
                next: "rawqqstring"
            }, {
                token: "string",
                regex: '"|$',
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "rawqstring": [{
                token: "string",
                regex: "\\\\$",
                next: "rawqstring"
            }, {
                token: "string",
                regex: "'|$",
                next: "start"
            }, {
                defaultToken: "string"
            }],
        "fqqstring3": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string", // multi line """ string end
                regex: '"{3}',
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "fqstring3": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string", // multi line ''' string end
                regex: "'{3}",
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "fqqstring": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string",
                regex: "\\\\$",
                next: "fqqstring"
            }, {
                token: "string",
                regex: '"|$',
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "fqstring": [{
                token: "constant.language.escape",
                regex: stringEscape
            }, {
                token: "string",
                regex: "'|$",
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "rfqqstring3": [{
                token: "string", // multi line """ string end
                regex: '"{3}',
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "rfqstring3": [{
                token: "string", // multi line ''' string end
                regex: "'{3}",
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "rfqqstring": [{
                token: "string",
                regex: "\\\\$",
                next: "rfqqstring"
            }, {
                token: "string",
                regex: '"|$',
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "rfqstring": [{
                token: "string",
                regex: "'|$",
                next: "start"
            }, {
                token: "paren.lparen",
                regex: "{",
                push: "fqstringParRules"
            }, {
                defaultToken: "string"
            }],
        "fqstringParRules": [{
                token: "paren.lparen",
                regex: "[\\[\\(]"
            }, {
                token: "paren.rparen",
                regex: "[\\]\\)]"
            }, {
                token: "string",
                regex: "\\s+"
            }, {
                token: "string",
                regex: "'[^']*'"
            }, {
                token: "string",
                regex: '"[^"]*"'
            }, {
                token: "function.support",
                regex: "(!s|!r|!a)"
            }, {
                include: "constants"
            }, {
                token: 'paren.rparen',
                regex: "}",
                next: 'pop'
            }, {
                token: 'paren.lparen',
                regex: "{",
                push: "fqstringParRules"
            }],
        "constants": [{
                token: "constant.numeric", // imaginary
                regex: "(?:" + floatNumber + "|\\d+)[jJ]\\b"
            }, {
                token: "constant.numeric", // float
                regex: floatNumber
            }, {
                token: "constant.numeric", // long integer
                regex: integer + "[lL]\\b"
            }, {
                token: "constant.numeric", // integer
                regex: integer + "\\b"
            }, {
                token: ["punctuation", "function.support"], // method
                regex: "(\\.)([a-zA-Z_]+)\\b"
            }, {
                token: keywordMapper,
                regex: "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
            }]
    };
    this.normalizeRules();
};
oop.inherits(PythonHighlightRules, TextHighlightRules);
exports.PythonHighlightRules = PythonHighlightRules;

});

define("ace/mode/folding/pythonic",["require","exports","module","ace/lib/oop","ace/mode/folding/fold_mode"], function(require, exports, module){"use strict";
var oop = require("../../lib/oop");
var BaseFoldMode = require("./fold_mode").FoldMode;
var FoldMode = exports.FoldMode = function (markers) {
    this.foldingStartMarker = new RegExp("([\\[{])(?:\\s*)$|(" + markers + ")(?:\\s*)(?:#.*)?$");
};
oop.inherits(FoldMode, BaseFoldMode);
(function () {
    this.getFoldWidgetRange = function (session, foldStyle, row) {
        var line = session.getLine(row);
        var match = line.match(this.foldingStartMarker);
        if (match) {
            if (match[1])
                return this.openingBracketBlock(session, match[1], row, match.index);
            if (match[2])
                return this.indentationBlock(session, row, match.index + match[2].length);
            return this.indentationBlock(session, row);
        }
    };
}).call(FoldMode.prototype);

});

define("ace/mode/python",["require","exports","module","ace/lib/oop","ace/mode/text","ace/mode/python_highlight_rules","ace/mode/folding/pythonic","ace/range"], function(require, exports, module){"use strict";
var oop = require("../lib/oop");
var TextMode = require("./text").Mode;
var PythonHighlightRules = require("./python_highlight_rules").PythonHighlightRules;
var PythonFoldMode = require("./folding/pythonic").FoldMode;
var Range = require("../range").Range;
var Mode = function () {
    this.HighlightRules = PythonHighlightRules;
    this.foldingRules = new PythonFoldMode("\\:");
    this.$behaviour = this.$defaultBehaviour;
};
oop.inherits(Mode, TextMode);
(function () {
    this.lineCommentStart = "#";
    this.$pairQuotesAfter = {
        "'": /[ruf]/i,
        '"': /[ruf]/i
    };
    this.getNextLineIndent = function (state, line, tab) {
        var indent = this.$getIndent(line);
        var tokenizedLine = this.getTokenizer().getLineTokens(line, state);
        var tokens = tokenizedLine.tokens;
        if (tokens.length && tokens[tokens.length - 1].type == "comment") {
            return indent;
        }
        if (state == "start") {
            var match = line.match(/^.*[\{\(\[:]\s*$/);
            if (match) {
                indent += tab;
            }
        }
        return indent;
    };
    var outdents = {
        "pass": 1,
        "return": 1,
        "raise": 1,
        "break": 1,
        "continue": 1
    };
    this.checkOutdent = function (state, line, input) {
        if (input !== "\r\n" && input !== "\r" && input !== "\n")
            return false;
        var tokens = this.getTokenizer().getLineTokens(line.trim(), state).tokens;
        if (!tokens)
            return false;
        do {
            var last = tokens.pop();
        } while (last && (last.type == "comment" || (last.type == "text" && last.value.match(/^\s+$/))));
        if (!last)
            return false;
        return (last.type == "keyword" && outdents[last.value]);
    };
    this.autoOutdent = function (state, doc, row) {
        row += 1;
        var indent = this.$getIndent(doc.getLine(row));
        var tab = doc.getTabString();
        if (indent.slice(-tab.length) == tab)
            doc.remove(new Range(row, indent.length - tab.length, row, indent.length));
    };
    this.$id = "ace/mode/python";
    this.snippetFileId = "ace/snippets/python";
}).call(Mode.prototype);
exports.Mode = Mode;

});                (function() {
                    window.require(["ace/mode/python"], function(m) {
                        if (typeof module == "object" && typeof exports == "object" && module) {
                            module.exports = m;
                        }
                    });
                })();
            