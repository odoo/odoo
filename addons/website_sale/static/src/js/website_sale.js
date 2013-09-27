$(document).ready(function () {
    $(".oe_website_sale input[name='shipping_different']").change(function () {
        $(".oe_website_sale .js_shipping").toggle();
    });

    $payment = $(".oe_website_sale .js_payment");
    $("input[name='payment_type']", $payment).click(function (ev) {
        var payment_id = $(ev.currentTarget).val();
        $("div[data-id]", $payment).addClass("hidden");
        $("a.btn:last, div[data-id='"+payment_id+"']", $payment).removeClass("hidden");
    });

    // change for css
    $(document).on('mouseup', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    function set_my_cart_quantity(qty) {
        $(".my_cart_quantity").html(qty.toString().indexOf(".") > -1 ? qty : qty + '.0').removeClass("hidden");
    }

    $(".oe_website_sale .oe_mycart input.js_quantity").change(function () {
        var $input = $(this);
        var value = parseInt($input.val());
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/set_cart_json/", 'call', {'order_line_id': $input.data('id'), 'set_number': value})
            .then(function (data) {
                set_my_cart_quantity(data[1]);
                $input.val(data[0]);
                if (!data[0]) {
                    openerp.jsonRpc('/shop/add_cart_json/', 'call', {'order_line_id': $input.data('id')}).then(function (data) {
                        location.reload();
                    });
                }
            });
    });
    
    // hack to add and rome from cart with json
    $('.oe_website_sale a[href*="/add_cart/"], a[href*="/remove_cart/"]').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/shop/add_cart_json/", 'call', {'order_line_id': $link.data('id'), 'remove': $link.is('[href*="/remove_cart/"]')})
            .then(function (data) {
                if (!data[0]) {
                    location.reload();
                }
                set_my_cart_quantity(data[1]);
                $link.parent().find(".js_quantity").val(data[0]);
            });
        return false;
    });

    $('.js_publish_management .js_go_to_top,.js_publish_management .js_go_to_bottom').on('click', function () {
        var $data = $(this).parents(".js_publish_management:first");
        openerp.jsonRpc('/shop/change_sequence/', 'call', {'id': $data.data('id'), 'top': $(this).hasClass('js_go_to_top')});
    });

    $('.js_publish_management ul[name="style"] a').on('click', function () {
        var $a = $(this);
        var $li = $a.parent();
        var $data = $(this).parents(".js_publish_management:first");

        var data = $a.data();
        if (data.class.toLowerCase().indexOf('size_') === 0) {
            $('.js_publish_management ul[name="style"] li:has(a[data-class^="size_"])').removeClass("active");
        }
        $li.parent().removeClass("active");
        openerp.jsonRpc('/shop/change_styles/', 'call', {'id': $data.data('id'), 'style_id': data.value})
            .then(function (result) {
                $li.toggleClass("active", result);
            });
    });

});
