odoo.define('fg_custom.FgPosReceipt', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var super_posmodel = models.PosModel.prototype;

    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var partner_model = _.find(this.models, function (model){
                return model.model === 'res.partner';
            });
            partner_model.fields.push('x_type_of_business');

            return super_posmodel.initialize.call(this, session, attributes);
        }
    });

});