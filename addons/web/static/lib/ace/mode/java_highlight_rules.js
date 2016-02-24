define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var DocCommentHighlightRules = require("./doc_comment_highlight_rules").DocCommentHighlightRules;
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var JavaHighlightRules = function() {

    // taken from http://download.oracle.com/javase/tutorial/java/nutsandbolts/_keywords.html
    var keywords = (
    "abstract|continue|for|new|switch|" +
    "assert|default|goto|package|synchronized|" +
    "boolean|do|if|private|this|" +
    "break|double|implements|protected|throw|" +
    "byte|else|import|public|throws|" +
    "case|enum|instanceof|return|transient|" +
    "catch|extends|int|short|try|" +
    "char|final|interface|static|void|" +
    "class|finally|long|strictfp|volatile|" +
    "const|float|native|super|while"
    );

    var buildinConstants = ("null|Infinity|NaN|undefined");


    var langClasses = (
        "AbstractMethodError|AssertionError|ClassCircularityError|"+
        "ClassFormatError|Deprecated|EnumConstantNotPresentException|"+
        "ExceptionInInitializerError|IllegalAccessError|"+
        "IllegalThreadStateException|InstantiationError|InternalError|"+
        "NegativeArraySizeException|NoSuchFieldError|Override|Process|"+
        "ProcessBuilder|SecurityManager|StringIndexOutOfBoundsException|"+
        "SuppressWarnings|TypeNotPresentException|UnknownError|"+
        "UnsatisfiedLinkError|UnsupportedClassVersionError|VerifyError|"+
        "InstantiationException|IndexOutOfBoundsException|"+
        "ArrayIndexOutOfBoundsException|CloneNotSupportedException|"+
        "NoSuchFieldException|IllegalArgumentException|NumberFormatException|"+
        "SecurityException|Void|InheritableThreadLocal|IllegalStateException|"+
        "InterruptedException|NoSuchMethodException|IllegalAccessException|"+
        "UnsupportedOperationException|Enum|StrictMath|Package|Compiler|"+
        "Readable|Runtime|StringBuilder|Math|IncompatibleClassChangeError|"+
        "NoSuchMethodError|ThreadLocal|RuntimePermission|ArithmeticException|"+
        "NullPointerException|Long|Integer|Short|Byte|Double|Number|Float|"+
        "Character|Boolean|StackTraceElement|Appendable|StringBuffer|"+
        "Iterable|ThreadGroup|Runnable|Thread|IllegalMonitorStateException|"+
        "StackOverflowError|OutOfMemoryError|VirtualMachineError|"+
        "ArrayStoreException|ClassCastException|LinkageError|"+
        "NoClassDefFoundError|ClassNotFoundException|RuntimeException|"+
        "Exception|ThreadDeath|Error|Throwable|System|ClassLoader|"+
        "Cloneable|Class|CharSequence|Comparable|String|Object"
    );

    var keywordMapper = this.createKeywordMapper({
        "variable.language": "this",
        "keyword": keywords,
        "constant.language": buildinConstants,
        "support.function": langClasses
    }, "identifier");

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        "start" : [
            {
                token : "comment",
                regex : "\\/\\/.*$"
            },
            DocCommentHighlightRules.getStartRule("doc-start"),
            {
                token : "comment", // multi line comment
                regex : "\\/\\*",
                next : "comment"
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
                token : keywordMapper,
                // TODO: Unicode escape sequences
                // TODO: Unicode identifiers
                regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
            }, {
                token : "keyword.operator",
                regex : "!|\\$|%|&|\\*|\\-\\-|\\-|\\+\\+|\\+|~|===|==|=|!=|!==|<=|>=|<<=|>>=|>>>=|<>|<|>|!|&&|\\|\\||\\?\\:|\\*=|%=|\\+=|\\-=|&=|\\^=|\\b(?:in|instanceof|new|delete|typeof|void)"
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
        ],
        "comment" : [
            {
                token : "comment", // closing comment
                regex : ".*?\\*\\/",
                next : "start"
            }, {
                token : "comment", // comment spanning whole line
                regex : ".+"
            }
        ]
    };

    this.embedRules(DocCommentHighlightRules, "doc-",
        [ DocCommentHighlightRules.getEndRule("start") ]);
};

oop.inherits(JavaHighlightRules, TextHighlightRules);

exports.JavaHighlightRules = JavaHighlightRules;
});
