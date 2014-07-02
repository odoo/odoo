$(document).ready(function () {
$('.oe_website_sale').each(function () {
    var oe_website_sale = this;

    var $shippingDifferent = $("input[name='shipping_different']", oe_website_sale);
    if ($shippingDifferent.is(':checked')) {
       $(".js_shipping", oe_website_sale).show();
    }
    $shippingDifferent.change(function () {
        $(".js_shipping", oe_website_sale).toggle();
    });

    // change for css
    $(oe_website_sale).on('mouseup touchend', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    $(oe_website_sale).on("change", ".oe_cart input.js_quantity", function () {
        var $input = $(this);
        var value = parseInt($input.val(), 10);
        var line_id = parseInt($input.data('line-id'),10);
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/cart/update_json", 'call', {
            'line_id': line_id,
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
                $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                $("#cart_total").replaceWith(data['website_sale.total']);
            });
    });

    // hack to add and rome from cart with json
    $(oe_website_sale).on('click', 'a.js_add_cart_json', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.parent().parent().find("input");
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
        $input.val(quantity > min ? (quantity < max ? quantity : max) : min);
        $('input[name="'+$input.attr("name")+'"]').val(quantity > min ? (quantity < max ? quantity : max) : min);
        $input.change();
        return false;
    });

    $('.a-submit', oe_website_sale).off('click').on('click', function () {
        $(this).closest('form').submit();
    });
    $('form.js_attributes input, form.js_attributes select', oe_website_sale).on('change', function () {
        $(this).closest("form").submit();
    });

    // change price when they are variants
    $('form.js_add_cart_json label', oe_website_sale).on('mouseup touchend', function (ev) {
        var $label = $(this);
        var $price = $label.parents("form:first").find(".oe_price .oe_currency_value");
        if (!$price.data("price")) {
            $price.data("price", parseFloat($price.text()));
        }
        var value = $price.data("price") + parseFloat($label.find(".badge span").text() || 0);
        var dec = value % 1;
        $price.html(value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") ));
    });
    // hightlight selected color
    $('.css_attribute_color input', oe_website_sale).on('change', function (ev) {
        $('.css_attribute_color').removeClass("active");
        $('.css_attribute_color:has(input:checked)').addClass("active");
    });

    function price_to_str(price) {
        price = Math.round(price * 100) / 100;
        var dec = Math.round((price % 1) * 100);
        return price + (dec ? '' : '.0') + (dec%10 ? '' : '0');
    }

    $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change', function (ev) {
        var $ul = $(this).parents('ul.js_add_cart_variants:first');
        var $parent = $ul.closest('.js_product');
        var $product_id = $parent.find('input.product_id').first();
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var variant_ids = $ul.data("attribute_value_ids");
        var values = [];
        $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
            values.push(+$(this).val());
        });

        $parent.find("label").removeClass("text-muted css_not_available");

        var product_id = false;
        for (var k in variant_ids) {
            if (_.isEqual(variant_ids[k][1], values)) {
                $price.html(price_to_str(variant_ids[k][2]));
                $default_price.html(price_to_str(variant_ids[k][3]));
                $default_price.parent().toggle(variant_ids[k][3]-variant_ids[k][2]>0.2);
                product_id = variant_ids[k][0];
                break;
            }
        }

        if (product_id) {
            var $img = $(this).closest('tr.js_product, .oe_website_sale').find('span[data-oe-model^="product."][data-oe-type="image"] img');
            $img.attr("src", "/website/image?field=image&model=product.product&id="+product_id);
            $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                .data('oe-model', 'product.product').data('oe-id', product_id);
        }

        $parent.find("input.js_variant_change:radio, select.js_variant_change").each(function () {
            var $input = $(this);
            var id = +$input.val();
            var values = [id];

            $parent.find("ul:not(:has(input.js_variant_change[value='" + id + "'])) input.js_variant_change:checked, select").each(function () {
                values.push(+$(this).val());
            });

            for (var k in variant_ids) {
                if (!_.difference(values, variant_ids[k][1]).length) {
                    return;
                }
            }
            $input.closest("label").addClass("css_not_available");
            $input.find("option[value='" + id + "']").addClass("css_not_available");
        });

        if (product_id) {
            $parent.removeClass("css_not_available");
            $product_id.val(product_id);
            $parent.find(".js_check_product").removeAttr("disabled");
        } else {
            $parent.addClass("css_not_available");
            $product_id.val(0);
            $parent.find(".js_check_product").attr("disabled", "disabled");
        }
    });
    $('ul.js_add_cart_variants', oe_website_sale).each(function () {
        $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
    });

    $(oe_website_sale).on('change', "select[name='country_id']", function () {
        var $select = $("select[name='state_id']");
        $select.find("option:not(:first)").hide();
        var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
        $select.parent().toggle(nb>1);
    }).change();
    $(oe_website_sale).on('change', "select[name='shipping_country_id']", function () {
        var $select = $("select[name='shipping_state_id']");
        $select.find("option:not(:first)").hide();
        var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
        $select.parent().toggle(nb>1);
    }).change();
});
});
