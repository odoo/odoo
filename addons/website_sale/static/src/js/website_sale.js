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
    $('form.js_attributes input, form.js_attributes select').on('change', function () {
        $(this).closest("form").submit();
    });

    // change price when they are variants
    var $price = $(".oe_price .oe_currency_value");
    $('form.js_add_cart_json label').on('mouseup', function (ev) {
        ev.preventDefault();
        var $label = $(ev.currentTarget);
        if (!$price.data("price")) {
            $price.data("price", parseFloat($price.text()));
        }
        var value = $price.data("price") + parseFloat($label.find(".badge span").text() || 0);
        var dec = value % 1;
        $price.html(value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") ));
    });
    // hightlight selected color
    $('.css_attribute_color input').on('change', function (ev) {
        $('.css_attribute_color').removeClass("active");
        $('.css_attribute_color:has(input:checked)').addClass("active");
    });

    var $form_var = $('form.js_add_cart_variants');
    var variant_ids = $form_var.data("attribute_value_ids");
    $form_var.on('change', 'input, select', function (ev) {
        var values = [];
        $form_var.find("label").removeClass("text-muted css_not_available");
        $form_var.find(".a-submit").removeAttr("disabled");

        $form_var.find('input:checked, select').each(function () {
            values.push(+$(this).val());
        });
        var product_id = false;
        for (var k in variant_ids) {
            if (_.isEqual(variant_ids[k][1], values)) {
                var dec = variant_ids[k][2] % 1;
                product_id = variant_ids[k][0];
                $('input[name="product_id"]').val(product_id);
                $price.html(variant_ids[k][2] + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") ));
                break;
            }
        }

        if (product_id) {
            $("#product_detail .product_detail_img").attr("src", "/website/image?field=image&model=product.product&id="+product_id);
        }

        $form_var.find("input:radio, select").each(function () {
            var id = +$(this).val();
            var values = [id];
            $form_var.find(">ul>li:not(:has(input[value='" + id + "'])) input:checked, select").each(function () {
                values.push(+$(this).val());
            });
            for (var k in variant_ids) {
                if (!_.difference(values, variant_ids[k][1]).length) {
                    return;
                }
            }
            $(this).parents("label:not(.css_attribute_color):first").addClass("text-muted");
            $(this).parents("label.css_attribute_color:first").addClass("css_not_available");
            $(this).find("option[value='" + id + "']").addClass("css_not_available");
        });

        if (product_id) {
            $(".oe_price_h4").removeClass("hidden");
            $(".oe_not_available").addClass("hidden");
        } else {
            $(".oe_price_h4").addClass("hidden");
            $(".oe_not_available").removeClass("hidden");
            $form_var.find('input[name="product_id"]').val(0);
            $form_var.find(".a-submit").attr("disabled", "disabled");
        }
    });
    $form_var.find("input:first").trigger('change');

});
