define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextMode = require("./text").Mode;
var CSharpHighlightRules = require("./csharp_highlight_rules").CSharpHighlightRules;
var MatchingBraceOutdent = require("./matching_brace_outdent").MatchingBraceOutdent;
var CstyleBehaviour = require("./behaviour/cstyle").CstyleBehaviour;
var CStyleFoldMode = require("./folding/csharp").FoldMode;

var Mode = function() {
    this.HighlightRules = CSharpHighlightRules;
    this.$outdent = new MatchingBraceOutdent();
    this.$behaviour = new CstyleBehaviour();
    this.foldingRules = new CStyleFoldMode();
};
oop.inherits(Mode, TextMode);

(function() {
    
    this.lineCommentStart = "//";
    this.blockComment = {start: "/*", end: "*/"};
    
    this.getNextLineIndent = function(state, line, tab) {
        var indent = this.$getIndent(line);
  
        var tokenizedLine = this.getTokenizer().getLineTokens(line, state);
        var tokens = tokenizedLine.tokens;
  
        if (tokens.length && tokens[tokens.length-1].type == "comment") {
            return indent;
        }
    
        if (state == "start") {
            var match = line.match(/^.*[\{\(\[]\s*$/);
            if (match) {
                indent += tab;
            }
        }
  
        return indent;
    };

    this.checkOutdent = function(state, line, input) {
        return this.$outdent.checkOutdent(line, input);
    };
  
    this.autoOutdent = function(state, doc, row) {
        this.$outdent.autoOutdent(doc, row);
    };


    this.createWorker = function(session) {
        return null;
    };

    this.$id = "ace/mode/csharp";
}).call(Mode.prototype);

exports.Mode = Mode;
});
