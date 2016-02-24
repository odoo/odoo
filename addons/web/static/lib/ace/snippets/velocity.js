define(function(require, exports, module) {
"use strict";

exports.snippetText = require("../requirejs/text!./velocity.snippets");
exports.scope = "velocity";
exports.includeScopes = ["html", "javascript", "css"];

});
