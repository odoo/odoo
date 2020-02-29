odoo.define('sale_expense.sale_order_many2one', function (require) {
"use strict";

var FieldMany2One = require('web.relational_fields').FieldMany2One;
var FieldRegistry = require('web.field_registry');


var OrderField = FieldMany2One.extend({
    /**
     * hide the search more option from the dropdown menu
     * @override
     * @private
     * @returns {Object}
     */
    _manageSearchMore: function (values) {
        return values;
    }
});
FieldRegistry.add('sale_order_many2one', OrderField);
return OrderField;
});
