define(function(require, exports, module) {
'use strict';

var oop = require("../lib/oop");
var TextMode = require("./text").Mode;
var LuceneHighlightRules = require("./lucene_highlight_rules").LuceneHighlightRules;

var Mode = function() {
    this.HighlightRules = LuceneHighlightRules;
};

oop.inherits(Mode, TextMode);

(function() {
    this.$id = "ace/mode/lucene";
}).call(Mode.prototype);

exports.Mode = Mode;
});