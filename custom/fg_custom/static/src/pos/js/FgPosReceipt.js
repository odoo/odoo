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
    const rpc = require('web.rpc');
    const session = require('web.session');
    const concurrency = require('web.concurrency');
    const { Gui } = require('point_of_sale.Gui');
    const { float_is_zero,round_decimals } = require('web.utils');
    const dp = new concurrency.DropPrevious();
    var core = require('web.core');
    var _t = core._t;
    var super_ordermodel = models.Order.prototype;

    class CouponCode {
        /**
         * @param {string} code coupon code
         * @param {number} coupon_id id of coupon.coupon
         * @param {numnber} program_id id of coupon.program
         */
        constructor(code, coupon_id, program_id) {
            this.code = code;
            this.coupon_id = coupon_id;
            this.program_id = program_id;
        }
    }

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
                pos_si_trans_reference: this.pos_si_trans_reference,
                pos_trans_reference: this.pos_trans_reference,
                pos_refund_si_reference: this.pos_refund_si_reference,
                pos_refunded_id: this.pos_refunded_id,
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
             this.pos_si_trans_reference = json.pos_si_trans_reference;
             this.pos_trans_reference = json.pos_trans_reference;
             this.pos_refund_si_reference = json.pos_refund_si_reference;
             this.pos_refunded_id = json.pos_refunded_id;

        },
        export_for_printing: function(){
            var receipt = super_ordermodel.export_for_printing.apply(this, arguments);
            receipt.x_receipt_note= this.x_receipt_note;
            receipt.x_ext_source= this.x_ext_source;
            receipt.x_ext_order_ref= this.x_ext_order_ref;
            receipt.x_receipt_printed= this.x_receipt_printed;
            receipt.x_receipt_printed_date= this.x_receipt_printed_date;
            receipt.website_order_id= this.website_order_id;
            receipt.pos_si_trans_reference= this.pos_si_trans_reference;
            receipt.pos_trans_reference= this.pos_trans_reference;
            receipt.pos_refund_si_reference= this.pos_refund_si_reference;
            receipt.pos_refunded_id= this.pos_refunded_id;

            var val = {};
            var total_disc_amt = 0;
            _.each(receipt.orderlines, function(line){
                if(line.program_id && line.is_program_reward){
                    if(val[line.program_id]){
                        val[line.program_id] = [line.product_name , Math.abs(val[line.program_id][1]) + Math.abs(line.price_with_tax)]
                    }else{
                        val[line.program_id] = [line.product_name , Math.abs(line.price_with_tax)]
                    }
                }else{
                    if(line.price < 0 ){ // to display discount in the pos reprinting
                        line.is_program_reward = true; // set field to true for discount/promo items
                        total_disc_amt = total_disc_amt + Math.abs(line.price_with_tax);
                        val[line.program_id] = [line.product_name , total_disc_amt]
                    }
                }
            });
            receipt.program_reward_lines = val;
            return receipt;
        },

        activateCode: async function (code) {
            const promoProgram = this.pos.promo_programs.find(
                (program) => program.promo_barcode == code || program.promo_code == code
            );
            if (promoProgram && this.activePromoProgramIds.includes(promoProgram.id)) {
                Gui.showNotification('That promo code program has already been activated.');
            } else if (promoProgram) {
                const customer = this.get_client();
                if(!customer){
//                    Gui.showNotification('This order not available customer, first set custom.');
//                    Gui.showPopup('ErrorPopup', {
//                        title: _t("Set customer"),
//                        body: _t("This order not available customer, first set custom"),
//                    });
//                    return;

//                    if(promoProgram.fg_discount_type){
//                        if(promoProgram.fg_discount_type == 'is_pwd_discount' && !customer.x_pwd_id){
//    //                        Gui.showNotification('PWD ID not set on customer, first set custom.');
//                            Gui.showPopup('ErrorPopup', {
//                                title: _t("Set Discount"),
//                                body: _t("PWD ID not set on customer, first set custom."),
//                            });
//                            return;
//                        }
//                        if(promoProgram.fg_discount_type == 'is_senior_discount' && !customer.x_senior_id){
//    //                        Gui.showNotification('Senior ID not set on customer, first set custom.');
//                            Gui.showPopup('ErrorPopup', {
//                                title: _t("Set Discount"),
//                                body: _t("Senior ID not set on customer, first set custom."),
//                            });
//                            return;
//                        }
//                    }
                }
                // TODO these two operations should be atomic
                this.activePromoProgramIds.push(promoProgram.id);
                this.trigger('update-rewards');
            } else if (code in this.bookedCouponCodes) {
                Gui.showNotification('That coupon code has already been scanned and activated.');
            } else {
                const programIdsWithScannedCoupon = Object.values(this.bookedCouponCodes).map(
                    (couponCode) => couponCode.program_id
                );
                const customer = this.get_client();
                const { successful, payload } = await rpc.query({
                    model: 'pos.config',
                    method: 'use_coupon_code',
                    args: [
                        [this.pos.config.id],
                        code,
                        this.creation_date,
                        customer ? customer.id : false,
                        programIdsWithScannedCoupon,
                    ],
                    kwargs: { context: session.user_context },
                });
                if (successful) {
                    // TODO these two operations should be atomic
                    this.bookedCouponCodes[code] = new CouponCode(code, payload.coupon_id, payload.program_id);
                    this.trigger('update-rewards');
                } else {
                    Gui.showNotification(payload.error_message);
                }
            }
        },
    });

});


