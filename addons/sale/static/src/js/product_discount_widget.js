odoo.define('sale.product_discount', function (require) {
    "use strict";

    const BasicFields = require('web.basic_fields');
    const FieldsRegistry = require('web.field_registry');
    const UpdateAllLinesMixin = require('sale.UpdateAllLinesMixin');

    /**
     * The sale.product_discount widget is a simple widget extending FieldFloat
     *
     *
     * !!! WARNING !!!
     *
     * This widget is only designed for sale_order_line creation/updates.
     */
    const ProductDiscountWidget = BasicFields.FieldFloat.extend(UpdateAllLinesMixin, {
        _getUpdateAllLinesAction: function () {
            return 'open_update_all_wizard';
        },
    });

    FieldsRegistry.add('product_discount', ProductDiscountWidget);

    return ProductDiscountWidget;

});
