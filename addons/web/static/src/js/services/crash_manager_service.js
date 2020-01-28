odoo.define('crash_manager.service', function (require) {
'use strict';

const { serviceRegistry } = require('web.core');
const CrashManager = require('web.CrashManager').CrashManager;

serviceRegistry.add('crashManager', CrashManager);

});
