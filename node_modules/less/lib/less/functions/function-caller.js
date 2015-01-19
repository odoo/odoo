var functionRegistry = require("./function-registry");

var functionCaller = function(name, context, index, currentFileInfo) {
    this.name = name.toLowerCase();
    this.func = functionRegistry.get(this.name);
    this.index = index;
    this.context = context;
    this.currentFileInfo = currentFileInfo;
};
functionCaller.prototype.isValid = function() {
    return Boolean(this.func);
};
functionCaller.prototype.call = function(args) {
    return this.func.apply(this, args);
};

module.exports = functionCaller;
