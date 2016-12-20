odoo.define('website_sale_coupon', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var _t = core._t;

$(document).ready(function () {
    $('body').on('click', '.check_coupon', function (ev) {
        var promocode = $("div.coupon_box").find("input[name='promo_code']").val();
        ajax.jsonRpc('/shop/apply_coupon', 'call', {'promo_code': promocode})
        .then(function(data) {
            if (data['error']){
                if ($("div.coupon_box").parent().find(".nocoupon_alert").length == 0){
                    $("div.coupon_box").append(
                        '<div class="alert alert-danger alert-dismissable nocoupon_alert" style="position: absolute; width: 262px; z-index:9999;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                         data['error']+
                        '</div>');
                }
            }
            if (data['generated_coupon']){
                if ($("div.coupon_box").parent().find(".nocoupon_alert").length == 0){
                    $("div.coupon_box").append(
                        '<div class="alert alert-success alert-dismissable nocoupon_alert" style="position: absolute; width: 262px; z-index:9999;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                         _.str.sprintf(_t("Your reward <b>%s</b> is available on a next order with this coupon code: %s"), data['generated_coupon']['reward'], data['generated_coupon']['code'])+
                        '</div>');
                }
            }
            location.reload();
        });
    });

});
});
