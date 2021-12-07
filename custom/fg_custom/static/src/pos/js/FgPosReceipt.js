odoo.define('fg_custom.FgPosReceipt', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var super_posmodel = models.PosModel.prototype;


    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var partner_model = _.find(this.models, function (model){
                return model.model === 'res.partner';
            });
            partner_model.fields.push('x_type_of_business', 'x_pwd_id', 'x_senior_id');
            //models.load_fields("res.partner", "x_type_of_business");
//            models.load_fields('pos.order', 'x_receipt_note');
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


//    var super_paymentmodel = models.Payment.prototype;
//    models.Payment = models.Payment.extend({
//        init_from_JSON: function(json) {
//             super_paymentmodel.init_from_JSON.apply(this, arguments);
//
//             this.x_card_number = json.x_card_number,
//             this.x_card_name = json.x_card_name,
//             this.cardholder_name = json.cardholder_name,
//             this.x_approval_no = json.x_approval_no,
//             this.x_batch_num = json.x_batch_num
//        },
//        export_as_JSON: function() {
//            let json = super_paymentmodel.export_as_JSON.apply(this, arguments);
//            return Object.assign(json, {
//                x_card_number: this.x_card_number,
//                x_card_name: this.x_card_name,
//                cardholder_name: this.cardholder_name,
//                x_approval_no: this.x_approval_no,
//                x_batch_num: this.x_batch_num
//            });
//            return json;
//        },
//        export_for_printing: function(){
//            var receipt = super_paymentmodel.export_for_printing.apply(this, arguments);
//            receipt.x_card_number= this.x_card_number,
//            receipt.x_card_name= this.x_card_name,
//            receipt.cardholder_name= this.cardholder_name,
//            receipt.x_approval_no= this.x_approval_no,
//            receipt.x_batch_num= this.x_batch_num
//            return receipt;
//
//        }
//    });



});