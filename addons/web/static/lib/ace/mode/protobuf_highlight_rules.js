define(function(require, exports, module) {
    "use strict";

    var oop = require("../lib/oop");
    var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

    var ProtobufHighlightRules = function() {

        var builtinTypes = "double|float|int32|int64|uint32|uint64|sint32|" +
                           "sint64|fixed32|fixed64|sfixed32|sfixed64|bool|" +
                           "string|bytes";
        var keywordDeclaration = "message|required|optional|repeated|package|" +
                                 "import|option|enum";

        var keywordMapper = this.createKeywordMapper({
            "keyword.declaration.protobuf": keywordDeclaration,
            "support.type": builtinTypes
        }, "identifier");

        this.$rules = {
            "start": [{
                    token: "comment",
                    regex: /\/\/.*$/
                }, {
                    token: "comment",
                    regex: /\/\*/,
                    next: "comment"
                }, {
                    token: "constant",
                    regex: "<[^>]+>"
                }, {
                    regex: "=",
                    token: "keyword.operator.assignment.protobuf"
                }, {
                    token : "string", // single line
                    regex : '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
                }, {
                    token : "string", // single line
                    regex : '[\'](?:(?:\\\\.)|(?:[^\'\\\\]))*?[\']'
                }, {
                    token: "constant.numeric", // hex
                    regex: "0[xX][0-9a-fA-F]+\\b"
                }, {
                    token: "constant.numeric", // float
                    regex: "[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?\\b"
                }, {
                    token: keywordMapper,
                    regex: "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
                }],
            "comment": [{
                    token: "comment", // closing comment
                    regex: ".*?\\*\\/",
                    next: "start"
                }, {
                    token: "comment", // comment spanning whole line
                    regex: ".+"
                }]
        };

        this.normalizeRules();
    };

    oop.inherits(ProtobufHighlightRules, TextHighlightRules);

    exports.ProtobufHighlightRules = ProtobufHighlightRules;
});