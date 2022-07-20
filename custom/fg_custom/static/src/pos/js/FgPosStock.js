odoo.define('fg_custom.FgPosStock', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var super_posmodel = models.PosModel.prototype;

     console.log(super_posmodel);
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var product_model = _.find(this.models, function (model){
                return model.model === 'product.product';
            });
            product_model.fields.push('qty_available');

            return super_posmodel.initialize.call(this, session, attributes);
        }
    });

});


