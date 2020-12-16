odoo.define('stock.BasicModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var localStorage = require('web.local_storage');

BasicModel.include({

    _invalidateCache: function (dataPoint) {
        this._super.apply(this, arguments);
        if (dataPoint.model === 'stock.warehouse' && !localStorage.getItem('running_tour')) {
            this.do_action('reload_context');
        }
    }
});
});
