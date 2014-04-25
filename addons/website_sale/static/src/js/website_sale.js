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

    $(".oe_website_sale .oe_mycart input.js_quantity").change(function (ev) {
        var $input = $(this);
        var $link = $(ev.currentTarget);
        var value = parseInt($input.val(), 10);
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/set_cart_json/", 'call', {'order_line_id': $input.data('id'), 'set_number': value})
            .then(function (data) {
                if (!data[0]) {
                    location.reload();
                    return;
                }
                set_my_cart_quantity(data[1]);
                $link.parents(".input-group:first").find(".js_quantity").val(data[0]);
                $('#mycart_total').replaceWith(data[3]);
            });
    });

    // hack to add and rome from cart with json
    $('.oe_website_sale a.js_add_cart_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");

        var add_cart = href.match(/add_cart\/([0-9]+)/);
        var product_id = add_cart && +add_cart[1] || false;

        var change_cart = href.match(/change_cart\/([0-9]+)/);
        var order_line_id = change_cart && +change_cart[1] || false;
        openerp.jsonRpc("/shop/add_cart_json/", 'call', {
                'product_id': product_id,
                'order_line_id': order_line_id,
                'remove': $link.is('[href*="remove"]')})
            .then(function (data) {
                if (!data[0]) {
                    location.reload();
                }
                set_my_cart_quantity(data[1]);
                $link.parents(".input-group:first").find(".js_quantity").val(data[0]);
                $('#mycart_total').replaceWith(data[3]);
            });
        return false;
    });

    $('.a-submit').on('click', function () {
        $(this).closest('form').submit();
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
        clearTimeout(js_slider_time);
        $form.submit();
    });
    $(".js_slider", $form).each(function() {
        var $slide = $(this);
        var $slider = $('<div>'+
                '<input type="hidden" name="att-'+$slide.data("id")+'-minmem" value="'+$slide.data("min")+'"/>'+
                '<input type="hidden" name="att-'+$slide.data("id")+'-maxmem" value="'+$slide.data("max")+'"/>'+
            '</div>');
        var $min = $("<input readonly name='att-"+$slide.data("id")+"-min'/>")
            .css("border", "0").css("width", "50%")
            .val($slide.data("min"));
        var $max = $("<input readonly name='att-"+$slide.data("id")+"-max'/>")
            .css("border", "0").css("width", "50%").css("text-align", "right")
            .val($slide.data("max"));
        $slide.append($min);
        $slide.append($max);
        $slide.append($slider);
        $slider.slider({
            range: true,
            min: +$slide.data("min"),
            max: +$slide.data("max"),
            values: [
                $slide.data("value-min") ? +$slide.data("value-min") : +$slide.data("min"),
                $slide.data("value-max") ? +$slide.data("value-max") : +$slide.data("max")
            ],
            change: function( event, ui ) {
                $min.val( ui.values[ 0 ] );
                $max.val( ui.values[ 1 ] );
                $form.submit();
            },
            slide: function( event, ui ) {
                $min.val( ui.values[ 0 ] );
                $max.val( ui.values[ 1 ] );
            }
        });
        $min.val( $slider.slider( "values", 0 ) );
        $max.val( $slider.slider( "values", 1 ) );
    });
});
