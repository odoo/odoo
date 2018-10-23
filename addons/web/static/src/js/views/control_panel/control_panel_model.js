odoo.define('web.ControlPanelModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

var ControlPanelModel = AbstractModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get: function () {
        return {};
    },
});

return ControlPanelModel;

});
