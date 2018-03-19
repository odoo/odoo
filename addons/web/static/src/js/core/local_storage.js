odoo.define('web.local_storage', function (require) {
'use strict';

var RamStorage = require('web.RamStorage');

// use a fake localStorage in RAM if the native localStorage is unavailable
// (e.g. private browsing in Safari)
var localStorage = window.localStorage;
try {
    var uid = new Date();
    localStorage.setItem(uid, uid);
    localStorage.removeItem(uid);
} catch (exception) {
    localStorage = new RamStorage();
}

return localStorage;

});
