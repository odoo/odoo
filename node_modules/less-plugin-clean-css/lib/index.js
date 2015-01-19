var getCleanCSSProcessor = require("./clean-css-processor"),
    usage = require("./usage"),
    parseOptions = require("./parse-options");

function LessPluginCleanCSS(options) {
    this.options = options;
};

LessPluginCleanCSS.prototype = {
    install: function(less, pluginManager) {
        var CleanCSSProcessor = getCleanCSSProcessor(less);
        pluginManager.addPostProcessor(new CleanCSSProcessor(this.options));
    },
    printUsage: function () {
        usage.printUsage();
    },
    setOptions: function(options) {
        this.options = parseOptions(options);
    },
    minVersion: [2, 1, 0]
};

module.exports = LessPluginCleanCSS;
