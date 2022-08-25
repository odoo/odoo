odoo.define('web.LocalStorageService', function (require) {
'use strict';

/**
 * This module defines a service to access the localStorage object.
 */

var AbstractStorageService = require('web.AbstractStorageService');
var core = require('web.core');
var localStorage = require('web.local_storage');

var LocalStorageService = AbstractStorageService.extend({
    storage: localStorage,
});

core.serviceRegistry.add('local_storage', LocalStorageService);

return LocalStorageService;

});
