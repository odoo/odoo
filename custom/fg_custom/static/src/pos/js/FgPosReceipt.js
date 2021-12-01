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
            //models.load_fields("res.partner", "x_type_of_business");
            models.load_fields('pos.order', 'x_receipt_note');
            return super_posmodel.initialize.call(this, session, attributes);
        },

    });

//    export_as_JSON: function() {
//        var orderLines, paymentLines;
//        orderLines = [];
//        this.orderlines.each(_.bind( function(item) {
//            return orderLines.push([0, 0, item.export_as_JSON()]);
//        }, this));
//        paymentLines = [];
//        this.paymentlines.each(_.bind( function(item) {
//            return paymentLines.push([0, 0, item.export_as_JSON()]);
//        }, this));
//        var json = {
//            name: this.get_name(),
//        };
//        return json;
//    }
    var models = require('point_of_sale.models');
    var super_ordermodel = models.Order.prototype;

    models.Order = models.Order.extend({
        init_from_JSON: function(json) {
             super_ordermodel.init_from_JSON.apply(this, arguments);

             this.x_receipt_note = json.x_receipt_note
        },
        export_as_JSON: function() {
            let json = super_ordermodel.export_as_JSON.apply(this, arguments);
            return Object.assign(json, {
                x_receipt_note: this.x_receipt_note
            });
            return json;
        },
        export_for_printing: function(){
            var receipt = super_ordermodel.export_for_printing.apply(this, arguments);
            receipt.x_receipt_note= this.x_receipt_note
            return receipt;

        }
    });



});