odoo.define('web.local_storage', function (require) {
'use strict';

var Class = require('web.Class');

// Compatibility with private browsing in Safari
// Use dict in case of local storage is disabled
var localStorage = window.localStorage;
try {
    var uid = new Date();
    localStorage.setItem(uid, uid);
    localStorage.removeItem(uid);
} catch (exception) {
    var storage = {};
    var RamStorage = Class.extend({
        setItem: function(key, value) {
            storage[key] = value;
        },
        getItem: function(key) {
            return storage[key];
        },
        removeItem: function(key) {
            delete storage[key];
        },
        clear: function() {
            storage = {};
        },
    });
    localStorage = new RamStorage();
}

return localStorage;

});
