/** @odoo-module alias=web.SessionStorageService **/

/**
 * This module defines a service to access the sessionStorage object.
 */

import AbstractStorageService from "web.AbstractStorageService";
import core from "web.core";
import sessionStorage from "web.sessionStorage";

var SessionStorageService = AbstractStorageService.extend({
    storage: sessionStorage,
});

core.serviceRegistry.add('session_storage', SessionStorageService);

export default SessionStorageService;
