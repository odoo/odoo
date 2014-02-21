$(document).ready(function () {
    var $shippingDifferent = $(".oe_website_sale input[name='shipping_different']");
    if ($shippingDifferent.is(':checked')) {
       $(".oe_website_sale .js_shipping").show();
    }
    $shippingDifferent.change(function () {
        $(".oe_website_sale .js_shipping").toggle();
    });

    // change for css
    $(document).on('mouseup', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    function set_my_cart_quantity(qty) {
        var $q = $(".my_cart_quantity");
        $q.parent().parent().removeClass("hidden", !qty);
        $q.html(qty)
            .hide()
            .fadeIn(600);
    }

    $(".oe_website_sale .oe_cart input.js_quantity").change(function () {
        var $input = $(this);
        var value = parseInt($input.val(), 10);
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/cart/update_json", 'call', {
            'product_id': parseInt($input.data('id'),10),
            'set_qty': value})
            .then(function (data) {
                if (!data.quantity) {
                    location.reload();
                    return;
                }
                set_my_cart_quantity(data.cart_quantity);
                $input.val(data.quantity);
            });
    });

    // hack to add and rome from cart with json
    $('.oe_website_sale a.js_add_cart_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.parent().parent().find("input");
        $input.val(($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10));
        $input.change();
        return false;
    });

    // change price when they are variants
    $('form.js_add_cart_json label').on('mouseup', function (ev) {
        ev.preventDefault();
        var $label = $(ev.currentTarget);
        var $price = $label.parent("form").find(".oe_price .oe_currency_value");
        if (!$price.data("price")) {
            $price.data("price", parseFloat($price.text()));
        }
        $price.html($price.data("price")+parseFloat($label.find(".badge span").text() || 0));
    });

    // attributes

    var js_slider_time = null;
    var $form = $("form.attributes");
    $form.on("change", "label input", function () {
        $form.submit();
    });
});
