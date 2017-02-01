$(document).ready(function () {

function update_product_image(event_source, product_id) {
    var $img = $(event_source).closest('tr.js_product, .oe_website_sale').find('span[data-oe-model^="product."][data-oe-type="image"] img:first, img.product_detail_img');
    $img.attr("src", "/website/image/product.product/" + product_id + "/image");
    $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
        .data('oe-model', 'product.product').data('oe-id', product_id);
}

$('.oe_website_sale').each(function () {
    var oe_website_sale = this;

    var $shippingDifferent = $("select[name='shipping_id']", oe_website_sale);
    $shippingDifferent.change(function (event) {
        var value = +$shippingDifferent.val();
        var data = $shippingDifferent.find("option:selected").data();
        var $snipping = $(".js_shipping", oe_website_sale);
        var $inputs = $snipping.find("input");
        var $selects = $snipping.find("select");

        $snipping.toggle(!!value);
        $inputs.attr("readonly", value <= 0 ? null : "readonly" ).prop("readonly", value <= 0 ? null : "readonly" );
        $selects.attr("disabled", value <= 0 ? null : "disabled" ).prop("disabled", value <= 0 ? null : "disabled" );

        $inputs.each(function () {
            $(this).val( data[$(this).attr("name")] || "" );
        });
    });

    $(oe_website_sale).on("change", 'input[name="add_qty"]', function (event) {
        product_ids = [];
        var product_dom = $(".js_product .js_add_cart_variants[data-attribute_value_ids]").last();
        if (!product_dom.length) {
            return;
        }
        _.each(product_dom.data("attribute_value_ids"), function(entry) {
            product_ids.push(entry[0]);});
        var qty = $(event.target).closest('form').find('input[name="add_qty"]').val();

        openerp.jsonRpc("/shop/get_unit_price", 'call', {'product_ids': product_ids,'add_qty': parseInt(qty)})
        .then(function (data) {
            var current = product_dom.data("attribute_value_ids");
            for(var j=0; j < current.length; j++){
                current[j][2] = data[current[j][0]];
            }
            product_dom.attr("data-attribute_value_ids", JSON.stringify(current)).trigger("change");
        });
    });

    // change for css
    $(oe_website_sale).on('mouseup touchend', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    $(oe_website_sale).find("input.js_quantity[data-product-id]").on("change", function () {
        var $input = $(this);
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val(), 10);
        var $dom = $(this).closest('tr');
        var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'),10);
        var product_id = parseInt($input.data('product-id'),10);
        var product_ids = [product_id];
        if (isNaN(value)) value = 0;
        $dom_optional.each(function(){
            $(this).find('.js_quantity').text(value);
            product_ids.push($(this).find('span[data-product-id]').data('product-id'));
        });
        $input.data('update_change', true);
        openerp.jsonRpc("/shop/get_unit_price", 'call', {
            'product_ids': product_ids,
            'add_qty': value,
            'use_order_pricelist': true,
            'line_id': line_id})
        .then(function (res) {
            //basic case
            $dom.find('span.oe_currency_value').last().text(price_to_str(res[product_id]));
            $dom.find('.text-danger').toggle(res[product_id]<default_price && (default_price-res[product_id] > default_price/100));
            //optional case
            $dom_optional.each(function(){
                var id = $(this).find('span[data-product-id]').data('product-id');
                var price = parseFloat($(this).find(".text-danger > span.oe_currency_value").text());
                $(this).find("span.oe_currency_value").last().text(price_to_str(res[id]));
                $(this).find('.text-danger').toggle(res[id]<price && (price-res[id]>price/100));
            });
            openerp.jsonRpc("/shop/cart/update_json", 'call', {
            'line_id': line_id,
            'product_id': parseInt($input.data('product-id'),10),
            'set_qty': value})
            .then(function (data) {
                $input.data('update_change', false);
                if (value !== parseInt($input.val(), 10)) {
                    $input.trigger('change');
                    return;
                }
                if (!data.quantity) {
                    location.reload(true);
                    return;
                }
                var $q = $(".my_cart_quantity");
                $q.parent().parent().removeClass("hidden", !data.quantity);
                $q.html(data.cart_quantity).hide().fadeIn(600);

                $input.val(data.quantity);
                $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                $("#cart_total").replaceWith(data['website_sale.total']);
                if (data.warning) {
                    var cart_alert = $('.oe_cart').parent().find('#data_warning');
                    if (cart_alert.length == 0) {
                        $('.oe_cart').prepend('<div class="alert alert-danger alert-dismissable" role="alert" id="data_warning">'+
                                '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning + '</div>');
                    }
                    else {
                        cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning);
                    }
                    $input.val(data.quantity);
                }
            });
        });
    });

    // hack to add and rome from cart with json
    $(oe_website_sale).on('click', 'a.js_add_cart_json', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.parent().find("input");
        var product_id = +$input.closest('*:has(input[name="product_id"])').find('input[name="product_id"]').val();
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
        // if they are more of one input for this product (eg: option modal)
        $('input[name="'+$input.attr("name")+'"]').add($input).filter(function () {
            var $prod = $(this).closest('*:has(input[name="product_id"])');
            return !$prod.length || +$prod.find('input[name="product_id"]').val() === product_id;
        }).val(quantity > min ? (quantity < max ? quantity : max) : min);
        $input.change();
        return false;
    });

    $('.oe_website_sale .a-submit, #comment .a-submit').off('click').on('click', function (event) {
        if (!event.isDefaultPrevented() && !$(this).is(".disabled")) {
            $(this).closest('form').submit();
        }
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

    // Copy from core.js that is not available in front end.
    function intersperse(str, indices, separator) {
        separator = separator || '';
        var result = [], last = str.length;

        for(var i=0; i<indices.length; ++i) {
            var section = indices[i];
            if (section === -1 || last <= 0) { break; }
            else if(section === 0 && i === 0) { break; }
            else if (section === 0) { section = indices[--i]; }
            result.push(str.substring(last-section, last));
            last -= section;
        }
        var s = str.substring(0, last);
        if (s) { result.push(s); }
        return result.reverse().join(separator);
    }
    function insert_thousand_seps(num) {
        var l10n = openerp._t.database.parameters;
        var negative = num[0] === '-';
        num = (negative ? num.slice(1) : num);
        // retro-compatibilit: if no website_id and so l10n.grouping = []
        var grouping = l10n.grouping instanceof Array ? l10n.grouping : JSON.parse(l10n.grouping);
        return (negative ? '-' : '') + intersperse(
            num, grouping, l10n.thousands_sep);
    }

    function price_to_str(price) {
        var l10n = openerp._t.database.parameters;
        var precision = 2;
        if ($(".decimal_precision").length) {
            var dec_precision = $(".decimal_precision").first().data('precision');
            //Math.log10 is not implemented in phantomJS
            dec_precision = Math.round(Math.log(1/parseFloat(dec_precision))/Math.log(10));
            if (!isNaN(dec_precision)) {
                precision = dec_precision;
            }
        }
        var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
        formatted[0] = insert_thousand_seps(formatted[0]);
        return formatted.join(l10n.decimal_point);
    }

    $(oe_website_sale).on('change', 'input.js_product_change', function (ev) {
        var $parent = $(this).closest('.js_product');
        $parent.find(".oe_default_price:first .oe_currency_value").html( price_to_str(+$(this).data('lst_price')) );
        $parent.find(".oe_price:first .oe_currency_value").html(price_to_str(+$(this).data('price')) );
        update_product_image(this, +$(this).val());
    });

    $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
        var $ul = $(ev.target).closest('.js_add_cart_variants');
        var $parent = $ul.closest('.js_product');
        var $product_id = $parent.find('input.product_id').first();
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        var variant_ids = $ul.data("attribute_value_ids");
        var values = [];
        $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
            values.push(+$(this).val());
        });

        $parent.find("label").removeClass("text-muted css_not_available");

        var product_id = false;
        for (var k in variant_ids) {
            if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                openerp.website.ready().then(function() {
                    $price.html(price_to_str(variant_ids[k][2]));
                    $default_price.html(price_to_str(variant_ids[k][3]));
                });
                if (variant_ids[k][3]-variant_ids[k][2]>0.2) {
                    $default_price.closest('.oe_website_sale').addClass("discount");
                    $optional_price.closest('.oe_optional').show().css('text-decoration', 'line-through');
                } else {
                    $default_price.closest('.oe_website_sale').removeClass("discount");
                    $optional_price.closest('.oe_optional').hide();
                }
                product_id = variant_ids[k][0];
                break;
            }
        }

        if (product_id) {
            update_product_image(this, product_id);
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
            $parent.find("#add_to_cart").removeClass("disabled");
        } else {
            $parent.addClass("css_not_available");
            $product_id.val(0);
            $parent.find("#add_to_cart").addClass("disabled");
        }
    });

    $('div.js_product', oe_website_sale).each(function () {
        $('input.js_product_change', this).first().trigger('change');
    });

    $('.js_add_cart_variants', oe_website_sale).each(function () {
        $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
    });

    $(oe_website_sale).on('change', "select[name='country_id']", function () {
        var $select = $("select[name='state_id']");
        $select.find("option:not(:first)").hide();
        var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
        $select.parent().toggle(nb>1);
    });
    $(oe_website_sale).find("select[name='country_id']").change();

    $(oe_website_sale).on('change', "select[name='shipping_country_id']", function () {
        var $select = $("select[name='shipping_state_id']");
        $select.find("option:not(:first)").hide();
        var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
        $select.parent().toggle(nb>1);
    });
    $(oe_website_sale).find("select[name='shipping_country_id']").change();
});
});
