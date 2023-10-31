odoo.define('stock.SingletonListRenderer', function (require) {
"use strict";

var core = require('web.core');
var ListRenderer = require('web.ListRenderer');

var _t = core._t;

/**
 * The purpose of this override is to disable line buttons when the row is edited.
 *
 */

var SingletonListRenderer = ListRenderer.extend({

    _disableRecordSelectors: function () {
        this._super.apply(this, arguments);
        var row = this._getRow(this._getRecordID(this.currentRow))[0];
        var lineButtons = row.querySelectorAll('button[name=action_set_inventory_quantity]');
        lineButtons.forEach(elem => elem.setAttribute('disabled', true));
    },
    /**
     * @private
     */
    _enableRecordSelectors: function () {
        this._super.apply(this, arguments);
        var lineButtons = this.el.querySelectorAll('button.disabled');
        lineButtons.forEach(elem => elem.removeAttribute('disabled'));
    },
});

return SingletonListRenderer;

});
