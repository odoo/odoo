odoo.define('web.sessionStorage', function (require) {
'use strict';

var RamStorage = require('web.RamStorage');

// use a fake sessionStorage in RAM if the native sessionStorage is unavailable
// (e.g. private browsing in Safari)
var sessionStorage = window.sessionStorage;
try {
    var uid = new Date();
    sessionStorage.setItem(uid, uid);
    sessionStorage.removeItem(uid);
} catch (exception) {
    sessionStorage = new RamStorage();
}

return sessionStorage;

});
