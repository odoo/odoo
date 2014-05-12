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

    $(".oe_website_sale .oe_cart input.js_quantity").change(function () {
        var $input = $(this);
        var value = parseInt($input.val(), 10);
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/cart/update_json", 'call', {
            'line_id': parseInt($input.data('line-id'),10),
            'product_id': parseInt($input.data('product-id'),10),
            'set_qty': value})
            .then(function (data) {
                if (!data.quantity) {
                    location.reload();
                    return;
                }
                var $q = $(".my_cart_quantity");
                $q.parent().parent().removeClass("hidden", !data.quantity);
                $q.html(data.cart_quantity).hide().fadeIn(600);
                $input.val(data.quantity);
                $("#cart_total").replaceWith(data['website_sale.total']);
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
