var path = require("path");
/**
 * Node Plugin Loader
 */
var PluginLoader = function(less) {
    this.less = less;
};
PluginLoader.prototype.tryLoadPlugin = function(name, argument) {
    var plugin = this.tryRequirePlugin(name);
    if (plugin) {
        // support plugins being a function
        // so that the plugin can be more usable programmatically
        if (typeof plugin === "function") {
            plugin = new plugin();
        }
        if (plugin.minVersion) {
            if (this.compareVersion(plugin.minVersion, this.less.version) < 0) {
                console.log("plugin " + name + " requires version " + this.versionToString(plugin.minVersion));
                return null;
            }
        }
        if (argument) {
            if (!plugin.setOptions) {
                console.log("options have been provided but the plugin " + name + "does not support any options");
                return null;
            }
            try {
                plugin.setOptions(argument);
            }
            catch(e) {
                console.log("Error setting options on plugin " + name);
                console.log(e.message);
                return null;
            }
        }
        return plugin;
    }
    return null;
};
PluginLoader.prototype.compareVersion = function(aVersion, bVersion) {
    for(var i = 0; i < aVersion.length; i++) {
        if (aVersion[i] !== bVersion[i]) {
            return parseInt(aVersion[i]) > parseInt(bVersion[i]) ? -1 : 1;
        }
    }
    return 0;
};
PluginLoader.prototype.versionToString = function(version) {
    var versionString = "";
    for(var i = 0; i < version.length; i++) {
        versionString += (versionString ? "." : "") + version[i];
    }
    return versionString;
};
PluginLoader.prototype.tryRequirePlugin = function(name) {
    // is at the same level as the less.js module
    try {
        return require("../../../" + name);
    }
    catch(e) {
    }
    // is installed as a sub dependency of the current folder
    try {
        return require(path.join(process.cwd(), "node_modules", name));
    }
    catch(e) {
    }
    // is referenced relative to the current directory
    try {
        return require(path.join(process.cwd(), name));
    }
    catch(e) {
    }
    // unlikely - would have to be a dependency of where this code was running (less.js)...
    if (name[0] !== '.') {
        try {
            return require(name);
        }
        catch(e) {
        }
    }
};
PluginLoader.prototype.printUsage = function(plugins) {
    for(var i = 0; i < plugins.length; i++) {
        var plugin = plugins[i];
        if (plugin.printUsage) {
            plugin.printUsage();
        }
    }
};
module.exports = PluginLoader;
