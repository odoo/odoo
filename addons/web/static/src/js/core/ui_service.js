odoo.define('web.UIService', function (require) {
'use strict';

const AbstractService = require('web.AbstractService');
const { serviceRegistry } = require('web.core');
const { blockUI, unblockUI } = require('web.framework');


const UIService = AbstractService.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    block(...args) {
        return blockUI(...args);
    },
    unblock(...args) {
        return unblockUI(...args);
    },
});

serviceRegistry.add('ui', UIService);

return UIService;

});
