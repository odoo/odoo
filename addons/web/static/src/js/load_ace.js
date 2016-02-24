 (function() {
"use strict";
odoo.__define__ = window.define;

 window.define = function(payload) {
    var module = odoo.ace_next_define;
    if (!odoo.__DEBUG__.services[module]) {
        odoo.__DEBUG__.factories[module] = payload;
        odoo.__DEBUG__.services[module] = null;
    }
};

/**
 * Get at functionality define()ed using the function above
 */
var _require = function(parentId, module, callback) {
    if (typeof module === "string") {
        var payload = lookup(parentId, module);
        if (payload !== undefined) {
            callback && callback();
            return payload;
        }
    } else if (Array.isArray(module)) {
        var params = [];
        for (var i = 0; i < module.length; ++i) {
            var dep = lookup(parentId, module[i]);
            if (dep === undefined) {
                return;
            }
            params.push(dep);
        }
        return callback && callback.apply(null, params) || true;
    }
};

var require = function(module, callback) {
    var packagedModule = _require("", module, callback);
    return packagedModule;
};

window.ace_require = require;

var normalizeModule = function(parentId, moduleName) {
    // normalize plugin requires
    if (moduleName.indexOf("!") !== -1) {
        var chunks = moduleName.split("!");
        return normalizeModule(parentId, chunks[0]) + "!" + normalizeModule(parentId, chunks[1]);
    }
    // normalize relative requires
    if (moduleName.charAt(0) == ".") {
        var base = parentId.split("/").slice(0, -1).join("/");
        moduleName = base + "/" + moduleName;

        while(moduleName.indexOf(".") !== -1 && previous != moduleName) {
            var previous = moduleName;
            moduleName = moduleName.replace(/\/\.\//, "/").replace(/[^\/]+\/\.\.\//, "");
        }
    }
    return moduleName;
};

/**
 * Internal function to lookup moduleNames and resolve them by calling the
 * definition function if needed.
 */
var lookup = function(parentId, moduleName) {
    moduleName = normalizeModule(parentId, moduleName);

    var module = odoo.__DEBUG__.services[moduleName];
    if (!module) {
        module = odoo.__DEBUG__.factories[moduleName];
        if (typeof module === 'function') {
            var exports = {};
            var mod = {
                id: moduleName,
                uri: '',
                exports: exports,
                packaged: true
            };

            var req = function(module, callback) {
                return _require(moduleName, module, callback);
            };

            var returnValue = module(req, exports, mod);
            exports = returnValue || mod.exports;
            odoo.__DEBUG__.services[moduleName] = exports;
            //delete odoo.__DEBUG__.factories[moduleName]; //TO ASK: Whether to delete payload once module is loaded
        }
        module = odoo.__DEBUG__.services[moduleName] = exports || module;
    }
    return module;
};

})();