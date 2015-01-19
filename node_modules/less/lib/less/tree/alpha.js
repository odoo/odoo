var Node = require("./node");

var Alpha = function (val) {
    this.value = val;
};
Alpha.prototype = new Node();
Alpha.prototype.type = "Alpha";

Alpha.prototype.accept = function (visitor) {
    this.value = visitor.visit(this.value);
};
Alpha.prototype.eval = function (context) {
    if (this.value.eval) { return new Alpha(this.value.eval(context)); }
    return this;
};
Alpha.prototype.genCSS = function (context, output) {
    output.add("alpha(opacity=");

    if (this.value.genCSS) {
        this.value.genCSS(context, output);
    } else {
        output.add(this.value);
    }

    output.add(")");
};

module.exports = Alpha;
