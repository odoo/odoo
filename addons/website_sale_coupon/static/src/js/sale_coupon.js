$(document).ready(function () {
    $('body').on('click', '.check_coupon', function (ev) {
        var promocode = $("div.coupon_box").find("input[name='promo']").val();
        openerp.jsonRpc('/shop/apply_coupon', 'call', {'promo': promocode})
        .then(function(data) {
            if (data['error']){
                nocoupon_alert = $("div.coupon_box").parent().find(".nocoupon_alert");
                if (nocoupon_alert.length == 0){
                    $("div.coupon_box").append(
                        '<div class="alert alert-danger alert-dismissable nocoupon_alert" style="position: absolute; width: 262px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                         data['error']+
                        '</div>');
                }
            }
            if (data['update_price']){
                location.reload();
            }
        });
    });
});
