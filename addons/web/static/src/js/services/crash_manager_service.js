odoo.define('crash_manager.service', function (require) {
'use strict';

const core = require('web.core');
const CrashManager = require('web.CrashManager').CrashManager;

core.serviceRegistry.add('crash_manager', CrashManager);

});
