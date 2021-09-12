odoo.define("aumet_pos_limit_discount.models", function (require) {
"use strict";

    const { Gui } = require('point_of_sale.Gui');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var qweb = core.qweb;
    var _t = core._t;

    models.load_fields('product.product',['limit_ch','limit_val']);

    var _super_Orderline = models.Orderline.prototype;
        models.Orderline = models.Orderline.extend({
            initialize: function (attributes, options) {
                var res = _super_Orderline.initialize.apply(this, arguments);
                return res;
            },
            play_wav: function() {
                var src = '';
                src = "/aumet_pos_limit_discount/static/src/sounds/zt.wav";
                $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
            },

             // sets a discount [0,100]%
             set_discount: function(discount){
                if(this.product.limit_ch === true && discount > this.product.limit_val){
                    this.play_wav();
                    Gui.showPopup('ConfirmPopup', {
                        title: this.pos.env._t('Exceeded Discount Limit!'),
                        body: this.pos.env._t(
                            "Sorry,"+discount+"% Is not Allowed!"+"\n"+"Maximum Discount On This Product Is: "+this.product.limit_val+"%"
                        ),
                    }).then(({ confirmed }) => {
                         if (confirmed) {
                             var parsed_discount = isNaN(parseFloat(this.product.limit_val)) ? 0 : field_utils.parse.float('' + this.product.limit_val);
                             var disc = Math.min(Math.max(parsed_discount || 0, 0),100);
                             this.discount = disc;
                             this.discountStr = '' + disc;
                             this.trigger('change',this);
                         }
                     });

                }
                else{
                    var parsed_discount = isNaN(parseFloat(discount)) ? 0 : field_utils.parse.float('' + discount);
                    var disc = Math.min(Math.max(parsed_discount || 0, 0),100);
                    this.discount = disc;
                    this.discountStr = '' + disc;
                    this.trigger('change',this);
                }
            },
        });

});