/** @odoo-module **/

/**
 * This module defines a service to access the localStorage object.
 */

import AbstractStorageService from "@web/legacy/js/core/abstract_storage_service";
import core from "@web/legacy/js/services/core";
import localStorage from "@web/legacy/js/core/local_storage";

var LocalStorageService = AbstractStorageService.extend({
    storage: localStorage,
});

core.serviceRegistry.add('local_storage', LocalStorageService);

export default LocalStorageService;
