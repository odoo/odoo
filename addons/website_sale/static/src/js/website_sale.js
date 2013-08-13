$(document).ready(function () {
    $('.oe_website_sale').on('click', '.js_publish, .js_unpublish', function (e) {
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


    $(".oe_website_sale input[name='shipping_different']").change(function() {
        $(".oe_website_sale .js_shipping").toggle();
    });

    $(".oe_website_sale .oe_mycart input").change(function() {
        var value = parseInt($(this).val());
        if (!isNaN(value)) {
            window.location.href = window.location.origin + window.location.pathname + 'set_cart/' + $(this).data('id') + '/' + value + '/';
        }
    });
    
});
