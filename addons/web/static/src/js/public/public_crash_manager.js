odoo.define('web.PublicCrashManager', function (require) {
"use strict";

const { serviceRegistry } = require('web.core');
const CrashManager = require('web.CrashManager').CrashManager;

const PublicCrashManager = CrashManager.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _displayWarning(message, title, options) {
        this.displayNotification(Object.assign({}, options, {
            title,
            message,
            sticky: true,
        }));
    },
});

serviceRegistry.add('crashManager', PublicCrashManager);

return {
    CrashManager: PublicCrashManager,
};

});
