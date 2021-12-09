odoo.define('fg_custom.FgPosAddPaymentDetails', function (require) {
    "use strict";

    var pos_model = require('point_of_sale.models');

    var _paylineproto = pos_model.Paymentline.prototype;
    pos_model.Paymentline = pos_model.Paymentline.extend({
        init_from_JSON: function (json) {
            _paylineproto.init_from_JSON.apply(this, arguments);
            this.x_check_number = json.x_check_number;
            this.x_issuing_bank = json.x_issuing_bank;
            this.x_check_date = json.x_check_date;
            this.x_card_number = json.x_card_number;
            this.x_card_name = json.x_card_name;
            this.cardholder_name = json.cardholder_name;
            this.x_approval_no = json.x_approval_no;
            this.x_batch_num = json.x_batch_num;
            this.x_gift_card_number = json.x_gift_card_number;
            this.x_gcash_refnum = json.x_gcash_refnum;
            this.x_gcash_customer = json.x_gcash_customer;
            this.x_gc_voucher_no = json.x_gc_voucher_no;
            this.x_gc_voucher_name = json.x_gc_voucher_name;
            this.x_gc_voucher_cust = json.x_gc_voucher_cust;

        },
        export_as_JSON: function () {
            return _.extend(_paylineproto.export_as_JSON.apply(this, arguments),
                                                                                   {x_check_number: this.x_check_number,
                                                                                    x_issuing_bank: this.x_issuing_bank,
                                                                                    x_check_date: this.x_check_date,
                                                                                    x_card_number:this.x_card_number,
                                                                                    x_card_name:this.x_card_name,
                                                                                    x_approval_no:this.x_approval_no,
                                                                                    x_batch_num:this.x_batch_num,
                                                                                    cardholder_name:this.cardholder_name,
                                                                                    x_gift_card_number:this.x_gift_card_number,
                                                                                    x_gcash_refnum:this.x_gcash_refnum,
                                                                                    x_gcash_customer:this.x_gcash_customer,
                                                                                    x_gc_voucher_no:this.x_gc_voucher_no,
                                                                                    x_gc_voucher_name:this.x_gc_voucher_name,
                                                                                    x_gc_voucher_cust:this.x_gc_voucher_cust
                                                                                    });
        },
        export_for_printing: function(){
            var paymentlines = _paylineproto.export_for_printing.apply(this, arguments);
            paymentlines.x_check_number= this.x_check_number;
            paymentlines.x_issuing_bank= this.x_issuing_bank;
            paymentlines.x_check_date= this.x_check_date;
            paymentlines.x_card_number= this.x_card_number;
            paymentlines.x_card_name= this.x_card_name;
            paymentlines.x_approval_no= this.x_approval_no;
            paymentlines.x_batch_num= this.x_batch_num;
            paymentlines.cardholder_name= this.cardholder_name;
            paymentlines.x_gift_card_number= this.x_gift_card_number;
            paymentlines.x_gcash_refnum= this.x_gcash_refnum;
            paymentlines.x_gcash_customer= this.x_gcash_customer;
            paymentlines.x_gc_voucher_no= this.x_gc_voucher_no;
            paymentlines.x_gc_voucher_name= this.x_gc_voucher_name;
            paymentlines.x_gc_voucher_cust= this.x_gc_voucher_cust;

            if(this.x_card_number!=null && this.x_card_number != '' && this.x_card_number){
                var mask='';
                if(this.x_card_number.length >=4){
                    var cardNumberLast4Digits = this.x_card_number.substring(this.x_card_number.length - 4)
                    for(var i=0; i< this.x_card_number.length-4; i++ ){
                        mask+='*';
                    }
                }else{
                    mask="**";
                    cardNumberLast4Digits=this.x_card_number;
                }

                paymentlines.x_card_number= mask+cardNumberLast4Digits;
            }

            return paymentlines;

        }

    });



});
