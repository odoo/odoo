var Node = require("./node"),
    FunctionCaller = require("../functions/function-caller");
//
// A function call node.
//
var Call = function (name, args, index, currentFileInfo) {
    this.name = name;
    this.args = args;
    this.index = index;
    this.currentFileInfo = currentFileInfo;
};
Call.prototype = new Node();
Call.prototype.type = "Call";
Call.prototype.accept = function (visitor) {
    if (this.args) {
        this.args = visitor.visitArray(this.args);
    }
};
//
// When evaluating a function call,
// we either find the function in the functionRegistry,
// in which case we call it, passing the  evaluated arguments,
// if this returns null or we cannot find the function, we
// simply print it out as it appeared originally [2].
//
// The reason why we evaluate the arguments, is in the case where
// we try to pass a variable to a function, like: `saturate(@color)`.
// The function should receive the value, not the variable.
//
Call.prototype.eval = function (context) {
    var args = this.args.map(function (a) { return a.eval(context); }),
        result, funcCaller = new FunctionCaller(this.name, context, this.index, this.currentFileInfo);

    if (funcCaller.isValid()) { // 1.
        try {
            result = funcCaller.call(args);
            if (result != null) {
                return result;
            }
        } catch (e) {
            throw { type: e.type || "Runtime",
                    message: "error evaluating function `" + this.name + "`" +
                             (e.message ? ': ' + e.message : ''),
                    index: this.index, filename: this.currentFileInfo.filename };
        }
    }

    return new Call(this.name, args, this.index, this.currentFileInfo);
};
Call.prototype.genCSS = function (context, output) {
    output.add(this.name + "(", this.currentFileInfo, this.index);

    for(var i = 0; i < this.args.length; i++) {
        this.args[i].genCSS(context, output);
        if (i + 1 < this.args.length) {
            output.add(", ");
        }
    }

    output.add(")");
};
module.exports = Call;
