define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var JavaScriptMode = require("./javascript").Mode;
var GroovyHighlightRules = require("./groovy_highlight_rules").GroovyHighlightRules;

var Mode = function() {
    JavaScriptMode.call(this);
    this.HighlightRules = GroovyHighlightRules;
};
oop.inherits(Mode, JavaScriptMode);

(function() {

    this.createWorker = function(session) {
        return null;
    };

    this.$id = "ace/mode/groovy";
}).call(Mode.prototype);

exports.Mode = Mode;
});
