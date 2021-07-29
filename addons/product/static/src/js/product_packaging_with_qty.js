odoo.define('product.product_packaging_with_qty', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry');
    const FieldMany2One = require('web.relational_fields').FieldMany2One;

    const ProductPackagingWithQty = FieldMany2One.extend({
        /**
         * @override
         * @private
         */
        _renderReadonly: function () {
            const $product_packaging_qty = $("<span>(&#xd7;" +this.recordData['product_packaging_qty'] + ")</span>");
            this.$el.text(this._formatValue(this.value));
            if (this.value) {
                this.setElement(this.$el.append($product_packaging_qty));
            }
        },
    });
    
    fieldRegistry.add('product_packaging_with_qty', ProductPackagingWithQty);
    
    return {
        ProductPackagingWithQty: ProductPackagingWithQty,
    };
    
});
