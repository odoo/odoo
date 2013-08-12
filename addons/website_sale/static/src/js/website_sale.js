$(document).ready(function () {
    $('.oe_ecommerce').on('click', '.js_publish, .js_unpublish', function (e) {
        e.preventDefault();
        var $link = $(this).parent();
        $link.find('.js_publish, .js_unpublish').addClass("hidden");
        var $unp = $link.find(".js_unpublish");
        var $p = $link.find(".js_publish");
        $.post('/shop/publish', {'id': $link.data('id')}, function (result) {
            if (+result) {
                $p.addClass("hidden");
                $unp.removeClass("hidden");
            } else {
                $p.removeClass("hidden");
                $unp.addClass("hidden");
            }
        });
    });


    var $checkout = $(".oe_ecommerce .oe_checkout");
    $(".oe_ecommerce input[name='shipping_different']").change(function() {
        $(".oe_ecommerce .js_shipping").toggle();
    });

});
