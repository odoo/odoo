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
        $.get("./set_cart/", {'order_line_id': $input.data('id'), 'set_number': value, 'json': true}, function (data) {
            var data = JSON.parse(data);
            set_my_cart_quantity(data[1]);
            $input.val(data[0]);
            if (!+data[0]) {
                $.get('/shop/remove_cart/', {'order_line_id': $input.data('id'), 'json': true,}, function (data) {
                    location.reload();
                });
            }
        });
    });

    $(".oe_website_sale #product_detail select[name='public_categ_id']").change(function () {
        var $select = $(this);
        $.get("/shop/change_category/"+$select.data('id')+"/", {'public_categ_id': $select.val()});
    });

    
    // hack to add and rome from cart with json
    $('.oe_website_sale a[href*="/add_cart/"], a[href*="/remove_cart/"]').on('click', function (ev) {
        ev.preventDefault();
        $link = $(ev.currentTarget);
        $.get($link.attr("href"), {'json': true}, function (data) {
            var data = JSON.parse(data);
            if (!+data[0]) {
                location.reload();
            }
            set_my_cart_quantity(data[1]);
            $link.parent().find(".js_quantity").val(data[0]);
        });
        return false;
    });
    $('.oe_website_sale form[action*="/add_cart/"]').on('submit', function (ev) {
        ev.preventDefault();
        $form = $(ev.currentTarget);
        $.get($form.attr("action"), {'product_id': $form.find('input[name="product_id"]:checked').val(), 'json': true}, function (data) {
            set_my_cart_quantity(JSON.parse(data)[1]);
        });
        return false;
    });

});
