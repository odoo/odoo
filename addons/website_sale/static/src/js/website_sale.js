$(document).ready(function () {
    var $shippingDifferent = $(".oe_website_sale input[name='shipping_different']");
    if ($shippingDifferent.is(':checked')) {
       $(".oe_website_sale .js_shipping").show();
    }
    $shippingDifferent.change(function () {
        $(".oe_website_sale .js_shipping").toggle();
    });

    var $payment = $(".oe_website_sale .js_payment");
    $payment.find("input[name='payment_type']").click(function (ev) {
        var payment_id = $(ev.currentTarget).val();
        $("div[data-id]", $payment).addClass("hidden");
        $("a.btn:last, div[data-id='"+payment_id+"']", $payment).removeClass("hidden");
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

    $(".oe_website_sale .oe_mycart input.js_quantity").change(function () {
        var $input = $(this);
        var value = parseInt($input.val());
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/set_cart_json/", 'call', {'order_line_id': $input.data('id'), 'set_number': value})
            .then(function (data) {
                set_my_cart_quantity(data[1]);
                $input.val(data[0]);
                if (!data[0]) {
                    location.reload();
                }
            });
    });

    // hack to add and rome from cart with json
    $('.oe_website_sale a.js_add_cart_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var product = $link.attr("href").match(/product_id=([0-9]+)/);
        var product_id = product ? +product[1] : 0;
        if (!product) {
            var line = $link.attr("href").match(/order_line_id=([0-9]+)/);
            order_line_id = line ? +line[1] : 0;
        }
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
                $('[data-oe-model="sale.order"][data-oe-field="amount_total"]').replaceWith(data[3]);
            });
        return false;
    });

    // change price when they are variants
    $('form.js_add_cart_json label').on('mouseup', function (ev) {
        ev.preventDefault();
        var $label = $(ev.currentTarget);
        var $price = $label.parent("form").find(".oe_price");
        if (!$price.data("price")) {
            $price.data("price", parseFloat($price.html()));
        }
        $price.html($price.data("price")+parseFloat($label.find(".badge span").html() || 0));
    });


    $(".js_slider").each(function() {
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
            slide: function( event, ui ) {
                $min.val( ui.values[ 0 ] );
                $max.val( ui.values[ 1 ] );
            }
        });
        $min.val( $slider.slider( "values", 0 ) );
        $max.val( $slider.slider( "values", 1 ) );
    });
});
