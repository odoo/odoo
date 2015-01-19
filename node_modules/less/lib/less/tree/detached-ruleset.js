var Node = require("./node"),
    contexts = require("../contexts");

var DetachedRuleset = function (ruleset, frames) {
    this.ruleset = ruleset;
    this.frames = frames;
};
DetachedRuleset.prototype = new Node();
DetachedRuleset.prototype.type = "DetachedRuleset";
DetachedRuleset.prototype.evalFirst = true;
DetachedRuleset.prototype.accept = function (visitor) {
    this.ruleset = visitor.visit(this.ruleset);
};
DetachedRuleset.prototype.eval = function (context) {
    var frames = this.frames || context.frames.slice(0);
    return new DetachedRuleset(this.ruleset, frames);
};
DetachedRuleset.prototype.callEval = function (context) {
    return this.ruleset.eval(this.frames ? new contexts.Eval(context, this.frames.concat(context.frames)) : context);
};
module.exports = DetachedRuleset;
