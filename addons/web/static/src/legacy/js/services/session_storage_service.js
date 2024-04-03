odoo.define('web.SessionStorageService', function (require) {
'use strict';

/**
 * This module defines a service to access the sessionStorage object.
 */

var AbstractStorageService = require('web.AbstractStorageService');
var core = require('web.core');
var sessionStorage = require('web.sessionStorage');

var SessionStorageService = AbstractStorageService.extend({
    storage: sessionStorage,
});

core.serviceRegistry.add('session_storage', SessionStorageService);

return SessionStorageService;

});
