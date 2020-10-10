
function wechatpay_query() {
    $(document).ready(function () {
        var order = $('.order').text();
        $.ajax({
            type: "GET",
            url: "/shop/wechatpay/result",
            data: {
                "order": order
            },
            dataType: "json",
            success: function (res) {
                if (res.result == 0) {
                    //跳转后续页面
                    window.location.href = '/payment/wechatpay/validate?order=' + order;
                }
            }
        });
    });
}
setInterval('wechatpay_query()', 5000);