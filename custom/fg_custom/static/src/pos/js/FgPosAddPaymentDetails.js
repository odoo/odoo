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
            this.x_gift_card_number = json.x_gift_card_number;

        },
        export_as_JSON: function () {
            return _.extend(_paylineproto.export_as_JSON.apply(this, arguments), {x_check_number: this.x_check_number,
                                                                                    x_issuing_bank: this.x_issuing_bank,
                                                                                    x_check_date: this.x_check_date,
                                                                                    x_card_number:this.x_card_number,
                                                                                    x_card_name:this.x_card_name,
                                                                                    cardholder_name:this.cardholder_name,
                                                                                    x_gift_card_number:this.x_gift_card_number
                                                                                    });
        }

    });



});
