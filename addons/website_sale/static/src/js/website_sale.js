$(document).ready(function () {
    $(".oe_website_sale input[name='shipping_different']").change(function () {
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

    $(document).on('click', '.js_publish_management .js_go_to_top,.js_publish_management .js_go_to_bottom', function (event) {
        var $a = $(event.currentTarget);
        var $data = $a.parents(".js_publish_management:first");
        openerp.jsonRpc('/shop/change_sequence/', 'call', {'id': $data.data('id'), 'top': $a.hasClass('js_go_to_top')});
    });

    $(document).on('click', '#products_grid .js_options ul[name="style"] a', function (event) {
        var $a = $(event.currentTarget);
        var $li = $a.parent();
        var $data = $a.parents(".js_options:first");
        var $product = $a.parents(".oe_product:first");

        $li.parent().removeClass("active");
        openerp.jsonRpc('/shop/change_styles/', 'call', {'id': $data.data('id'), 'style_id': $a.data("id")})
            .then(function (result) {
                $product.toggleClass($a.data("class"));
                $li.toggleClass("active", result);
            });
    });

    $(document).on('mouseenter', '#products_grid .js_options ul[name="size"] table', function (event) {
        $(event.currentTarget).addClass("oe_hover");
    });
    $(document).on('mouseleave', '#products_grid .js_options ul[name="size"] table', function (event) {
        $(event.currentTarget).removeClass("oe_hover");
    });
    $(document).on('mouseover', '#products_grid .js_options ul[name="size"] td', function (event) {
        var $td = $(event.currentTarget);
        var $table = $td.parents("table:first");
        var x = $td.index()+1;
        var y = $td.parent().index()+1;

        var tr = [];
        for (var yi=0; yi<y; yi++) tr.push("tr:eq("+yi+")");
        var $select_tr = $table.find(tr.join(","));
        var td = [];
        for (var xi=0; xi<x; xi++) td.push("td:eq("+xi+")");
        var $select_td = $select_tr.find(td.join(","));

        $table.find("td").removeClass("select");
        $select_td.addClass("select");
    });
    $(document).on('click', '#products_grid .js_options ul[name="size"] td', function (event) {
        var $td = $(event.currentTarget);
        var $data = $td.parents(".js_options:first");
        var x = $td.index()+1;
        var y = $td.parent().index()+1;
        openerp.jsonRpc('/shop/change_size/', 'call', {'id': $data.data('id'), 'x': x, 'y': y})
            .then(function () {
                var search = location.search.replace(/\?|$/, '?enable_editor=1&');
                location.href = location.href.replace(/(\?|#).*/, search + location.hash);
            });
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
