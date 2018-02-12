odoo.define('web.LocalStorageService', function (require) {
'use strict';

var AbstractService = require('web.AbstractService');
var core = require('web.core');
var localStorage = require('web.local_storage');

var LocalStorageService = AbstractService.extend({
    name: 'local_storage',
    setItem: function(key, value) {
        localStorage.setItem(key,value);
    },
    getItem: function(key) {
        return localStorage.getItem(key);
    },
    removeItem: function(key) {
        localStorage.removeItem(key);
    },
    clear: function() {
        localStorage.clear();
    }
});

core.serviceRegistry.add('local_storage', LocalStorageService);

return LocalStorageService;

});
