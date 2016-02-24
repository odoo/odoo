define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var HtmlMode = require("./html").Mode;
var LuaMode = require("./lua").Mode;
var LuaPageHighlightRules = require("./luapage_highlight_rules").LuaPageHighlightRules;

var Mode = function() {
    HtmlMode.call(this);
    
    this.HighlightRules = LuaPageHighlightRules;
    this.createModeDelegates({
        "lua-": LuaMode
    });
};
oop.inherits(Mode, HtmlMode);

(function() {
    this.$id = "ace/mode/luapage";
}).call(Mode.prototype);

exports.Mode = Mode;
});