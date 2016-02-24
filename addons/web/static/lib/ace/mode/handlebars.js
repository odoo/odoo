/* global define */

define(function(require, exports, module) {
  "use strict";

var oop = require("../lib/oop");
var HtmlMode = require("./html").Mode;
var HandlebarsHighlightRules = require("./handlebars_highlight_rules").HandlebarsHighlightRules;
var HtmlBehaviour = require("./behaviour/html").HtmlBehaviour;
var HtmlFoldMode = require("./folding/html").FoldMode;

var Mode = function() {
    HtmlMode.call(this);
    this.HighlightRules = HandlebarsHighlightRules;
    this.$behaviour = new HtmlBehaviour();
    
    this.foldingRules = new HtmlFoldMode();
};

oop.inherits(Mode, HtmlMode);

(function() {
    this.blockComment = {start: "{{!--", end: "--}}"};
    this.$id = "ace/mode/handlebars";
}).call(Mode.prototype);

exports.Mode = Mode;
});
