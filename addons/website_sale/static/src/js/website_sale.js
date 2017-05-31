odoo.define('website_sale.cart', function (require) {
"use strict";

var base = require('web_editor.base');
var core = require('web.core');
var _t = core._t;

var shopping_cart_link = $('ul#top_menu li a[href$="/shop/cart"]');
var shopping_cart_link_counter;
shopping_cart_link.popover({
    trigger: 'manual',
    animation: true,
    html: true,
    title: function () {
        return _t("My Cart");
    },
    container: 'body',
    placement: 'auto',
    template: '<div class="popover mycart-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-title"></h3><div class="popover-content"></div></div>'
}).on("mouseenter",function () {
    var self = this;
    clearTimeout(shopping_cart_link_counter);
    shopping_cart_link.not(self).popover('hide');
    shopping_cart_link_counter = setTimeout(function(){
        if($(self).is(':hover') && !$(".mycart-popover:visible").length)
        {
            $.get("/shop/cart", {'type': 'popover'})
                .then(function (data) {
                    $(self).data("bs.popover").options.content =  data;
                    $(self).popover("show");
                    $(".popover").on("mouseleave", function () {
                        $(self).trigger('mouseleave');
                    });
                });
        }
    }, 100);
}).on("mouseleave", function () {
    var self = this;
    setTimeout(function () {
        if (!$(".popover:hover").length) {
            if(!$(self).is(':hover'))
            {
               $(self).popover('hide');
            }
        }
    }, 1000);
});

});

odoo.define('website_sale.website_sale', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var utils = require('web.utils');
var _t = core._t;
var base = require('web_editor.base');


if(!$('#o_shop_collapse_category, .oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '#o_shop_collapse_category, .oe_website_sale'");
}

function update_product_image(event_source, product_id) {
    var $img = $(event_source).closest('tr.js_product, .oe_website_sale').find('span[data-oe-model^="product."][data-oe-type="image"] img:first, img.product_detail_img');
    $img.attr("src", "/web/image/product.product/" + product_id + "/image");
    $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
        .data('oe-model', 'product.product').data('oe-id', product_id);
}

$('#o_shop_collapse_category').on('click', '.fa-chevron-right',function(){
    $(this).parent().siblings().find('.fa-chevron-down:first').click();
    $(this).parents('li').find('ul:first').show('normal');
    $(this).toggleClass('fa-chevron-down fa-chevron-right');
});

$('#o_shop_collapse_category').on('click', '.fa-chevron-down',function(){
    $(this).parent().find('ul:first').hide('normal');
    $(this).toggleClass('fa-chevron-down fa-chevron-right');
});

$('.oe_website_sale').each(function () {
    var oe_website_sale = this;

    var $shippingDifferent = $("select[name='shipping_id']", oe_website_sale);
    $shippingDifferent.change(function () {
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

        $selects.filter('[name="shipping_country_id"]').val(data['shipping_country_id']).change();
        $selects.filter('[name="shipping_state_id"]').val(data['shipping_state_id']);
    });

    $(oe_website_sale).on("change", 'input[name="add_qty"]', function (event) {
        var product_ids = [];
        var product_dom = $(".js_product .js_add_cart_variants[data-attribute_value_ids]").last();
        if (!product_dom.length) {
            return;
        }
        _.each(product_dom.data("attribute_value_ids"), function(entry) {
            product_ids.push(entry[0]);});
        var qty = $(event.target).closest('form').find('input[name="add_qty"]').val();

        if ($("#product_detail").length) {
            // display the reduction from the pricelist in function of the quantity
            ajax.jsonRpc("/shop/get_unit_price", 'call', {'product_ids': product_ids,'add_qty': parseInt(qty)})
            .then(function (data) {
                var current = product_dom.data("attribute_value_ids");
                for(var j=0; j < current.length; j++){
                    current[j][2] = data[current[j][0]];
                }
                product_dom.attr("data-attribute_value_ids", JSON.stringify(current)).trigger("change");
            });
        }
    });

    // change for css
    $(oe_website_sale).on('mouseup touchend', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    var clickwatch = (function(){
          var timer = 0;
          return function(callback, ms){
            clearTimeout(timer);
            timer = setTimeout(callback, ms);
          };
    })();

    $(oe_website_sale).on("change", ".oe_cart input.js_quantity[data-product-id]", function () {
      var $input = $(this);
        if ($input.data('update_change')) {
            return;
        }
      var value = parseInt($input.val() || 0, 10);
      var $dom = $(this).closest('tr');
      var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
      var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
      var line_id = parseInt($input.data('line-id'),10);
      var product_id = parseInt($input.data('product-id'),10);
      var product_ids = [product_id];
      clickwatch(function(){

        $dom_optional.each(function(){
            $(this).find('.js_quantity').text(value);
            product_ids.push($(this).find('span[data-product-id]').data('product-id'));
        });
        $input.data('update_change', true);

        ajax.jsonRpc("/shop/cart/update_json", 'call', {
        'line_id': line_id,
        'product_id': parseInt($input.data('product-id'),10),
        'set_qty': value})
        .then(function (data) {
            $input.data('update_change', false);
            if (value !== parseInt($input.val() || 0, 10)) {
                $input.trigger('change');
                return;
            }
            var $q = $(".my_cart_quantity");
            if (data.cart_quantity) {
                $q.parent().parent().removeClass("hidden");
            }
            else {
                $q.parent().parent().addClass("hidden");
                $('a[href^="/shop/checkout"]').addClass("hidden")
            }
            $q.html(data.cart_quantity).hide().fadeIn(600);

            $input.val(data.quantity);
            $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);

            $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();

            if (data.warning) {
                var cart_alert = $('.oe_cart').parent().find('#data_warning');
                if (cart_alert.length === 0) {
                    $('.oe_cart').prepend('<div class="alert alert-danger alert-dismissable" role="alert" id="data_warning">'+
                            '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning + '</div>');
                }
                else {
                    cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning);
                }
                $input.val(data.quantity);
            }
        });
      }, 500);
    });

    $(oe_website_sale).on("click", ".oe_cart a.js_add_suggested_products", function () {
        $(this).prev('input').val(1).trigger('change');
    });


    // hack to add and rome from cart with json
    $(oe_website_sale).on('click', 'a.js_add_cart_json', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.parent().find("input");
        var product_id = +$input.closest('*:has(input[name="product_id"])').find('input[name="product_id"]').val();
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
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
    $('form.js_attributes input, form.js_attributes select', oe_website_sale).on('change', function (event) {
        if (!event.isDefaultPrevented()) {
            $(this).closest("form").submit();
        }
    });

    // change price when they are variants
    $('form.js_add_cart_json label', oe_website_sale).on('mouseup touchend', function () {
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
    $('.css_attribute_color input', oe_website_sale).on('change', function () {
        $('.css_attribute_color').removeClass("active");
        $('.css_attribute_color:has(input:checked)').addClass("active");
    });

    function price_to_str(price) {
        var l10n = _t.database.parameters;
        var precision = 2;

        if ($(".decimal_precision").length) {
            precision = parseInt($(".decimal_precision").last().data('precision'));
        }
        var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
        formatted[0] = utils.insert_thousand_seps(formatted[0]);
        return formatted.join(l10n.decimal_point);
    }

    $(oe_website_sale).on('change', 'input.js_product_change', function () {
        var self = this;
        var $parent = $(this).closest('.js_product');
        $.when(base.ready()).then(function() {
            $parent.find(".oe_default_price:first .oe_currency_value").html( price_to_str(+$(self).data('lst_price')) );
            $parent.find(".oe_price:first .oe_currency_value").html(price_to_str(+$(self).data('price')) );
        });
        update_product_image(this, +$(this).val());
    });

    $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
        var $ul = $(ev.target).closest('.js_add_cart_variants');
        var $parent = $ul.closest('.js_product');
        var $product_id = $parent.find('input.product_id').first();
        var $price = $parent.find(".oe_price:first .oe_currency_value")
            .add($('#product_confirmation').find(".oe_price"));
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value")
            .add($('#product_confirmation').find(".oe_default_price:first .oe_currency_value"));
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
                $.when(base.ready()).then(function() {
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

    $("select[name='state_id']").each(function(){
        $(this).data('options', $(this).find('option:not(:first)'));
    });
    $(oe_website_sale).on('change', "select[name='country_id']", function () {
        var select = $("select[name='state_id']:enabled");
        var state_options = select.data('options');
        var selected_state = select.val();
        state_options.detach();
        var displayed_state = state_options.filter("[data-country_id="+($(this).val() || 0)+"]");
        select.val(selected_state);
        var nb = displayed_state.appendTo(select).show().size();
        select.parent().toggle(nb>=1);
    });
    $(oe_website_sale).find("select[name='country_id']").change();

    var shipping_state_options = $("select[name='shipping_state_id'] option:not(:first)");
    $(oe_website_sale).on('change', "select[name='shipping_country_id']", function () {
        var select = $("select[name='shipping_state_id']");
        var selected_state = select.val();
        shipping_state_options.detach();
        var displayed_state = shipping_state_options.filter("[data-country_id="+($(this).val() || 0)+"]");
        select.val(selected_state);
        var nb = displayed_state.appendTo(select).show().size();
        select.parent().toggle(nb>=1);
    });
    $(oe_website_sale).find("select[name='shipping_country_id']").change();
});

});
