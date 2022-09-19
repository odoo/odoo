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

    var models = require('point_of_sale.models');
    var super_ordermodel = models.Order.prototype;

    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            return super_ordermodel.initialize.apply(this, arguments);
        },
        export_as_JSON: function() {
            let json = super_ordermodel.export_as_JSON.apply(this, arguments);
            return Object.assign(json, {
                x_receipt_note: this.x_receipt_note,
                x_ext_source: this.x_ext_source,
                x_ext_order_ref: this.x_ext_order_ref,
                x_receipt_printed: this.x_receipt_printed,
                x_receipt_printed_date: this.x_receipt_printed_date,
                website_order_id: this.website_order_id,
            });
            return json;
        },
        init_from_JSON: function(json) {
             super_ordermodel.init_from_JSON.apply(this, arguments);
             this.x_receipt_note = json.x_receipt_note;
             this.x_ext_source = json.x_ext_source;
             this.x_ext_order_ref = json.x_ext_order_ref;
             this.x_receipt_printed = json.x_receipt_printed;
             this.x_receipt_printed_date = json.x_receipt_printed_date;
             this.website_order_id = json.website_order_id;
        },
        export_for_printing: function(){
            var receipt = super_ordermodel.export_for_printing.apply(this, arguments);
            receipt.x_receipt_note= this.x_receipt_note;
            receipt.x_ext_source= this.x_ext_source;
            receipt.x_ext_order_ref= this.x_ext_order_ref;
            receipt.x_receipt_printed= this.x_receipt_printed;
            receipt.x_receipt_printed_date= this.x_receipt_printed_date;
            receipt.website_order_id= this.website_order_id;
            var val = {};
            _.each(receipt.orderlines, function(line){
                if(line.program_id && line.is_program_reward){
                    if(val[line.program_id]){
                        val[line.program_id] = [line.product_name , Math.abs(val[line.program_id][1]) + Math.abs(line.price_with_tax)]
                    }else{
                        val[line.program_id] = [line.product_name , Math.abs(line.price_with_tax)]
                    }
                }
            });
            console.log('----val--', val)
            console.log('-=====-receipt----', receipt, this);
            receipt.program_reward_lines = val;
            return receipt;
        }
    });

});


