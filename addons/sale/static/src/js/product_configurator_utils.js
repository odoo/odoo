odoo.define('sale.product_configurator_utils', function (require) {
    'use strict';
    var core = require('web.core');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var _t = core._t;

    /**
     * returns the formatted price
     * @param {float} price 
     */
    function _priceToStr (price) {
        var l10n = _t.database.parameters;
        var precision = 2;

        if ($(".decimal_precision").length) {
            precision = parseInt($(".decimal_precision").last().data('precision'));
        }
        var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
        formatted[0] = utils.insert_thousand_seps(formatted[0]);
        return formatted.join(l10n.decimal_point);
    }

    /**
     * When a product is added or when the quantity is changed, 
     * we need to refresh the total price row
     * TODO (awa): add a container context to avoid global selectors ?
     */
    function computePriceTotal (){
        if($('.js_price_total').length){
            var price = 0;
            $('.js_product.in_cart').each(function(){
                var quantity = parseInt($('input[name="add_qty"]').first().val());
                price += parseFloat($(this).find('.js_raw_price').html()) * quantity;
            });

            $('.js_price_total .oe_currency_value').html(_priceToStr(parseFloat(price)));
        }
    }

    function _updateProductImage ($productContainer, product_id, imagesSize) {
        var $img;
        var imageSrc = '/web/image?model=product.product&id={0}&field={1}'
            .replace("{0}", product_id)
            .replace("{1}", imagesSize ? ('image_' + imagesSize) : 'image');
        if ($productContainer.find('#o-carousel-product').length) {
            $img = $productContainer.find('img.js_variant_img');
            $img.attr("src", imageSrc);
            $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                .data('oe-model', 'product.product').data('oe-id', product_id);

            var $thumbnail = $productContainer.find('img.js_variant_img_small');
            if ($thumbnail.length !== 0) { // if only one, thumbnails are not displayed
                $thumbnail.attr("src", "/web/image/product.product/" + product_id + "/image/90x90");
                $('.carousel').carousel(0);
            }
        }
        else {
            $img = $productContainer.find('span[data-oe-model^="product."][data-oe-type="image"] img:first, img.product_detail_img, span.variant_image img');
            $img.attr("src", imageSrc);
            $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                .data('oe-model', 'product.product').data('oe-id', product_id);
        }
        // reset zooming constructs
        $img.filter('[data-zoom-image]').attr('data-zoom-image', $img.attr('src'));
        if ($img.data('zoomOdoo') !== undefined) {
            $img.data('zoomOdoo').isReady = false;
        }
    }

    /**
     * When a variant is changed, this will compute:
     * - If the selected combination is available or not
     * - The extra price if applicable
     * - The display name of the product ("Customizable desk (White, Steel)")
     * TODO (awa): change ugly [0], [1], [2], ... to a dict
     */
    function onChangeVariant (ev, imagesSize) {
        var $parent = $(ev.target).closest('.js_product');
        var $ul = $parent.find('.js_add_cart_variants');
        var $product_id = $parent.find('.product_id').first();
        var $product_display_name = $parent.find('.product_display_name').first();
        var $product_raw_price = $parent.find('.js_raw_price').first();
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        var variant_ids = $ul.data("attribute_value_ids");
        var values = [];
        var unchanged_values = $parent.find('div.oe_unchanged_value_ids').data('unchanged_value_ids') || [];

        _.each($parent.find('input.js_variant_change:checked, select.js_variant_change'), function (el) {
            values.push(+$(el).val());
        });
        values = values.concat(unchanged_values);
        var list_variant_id = parseInt($parent.find('input.js_product_change:checked').val());

        $parent.find("label").removeClass("text-muted css_not_available");

        var product_id = false;
        var display_name = false;
        var product_raw_price = false;
        for (var k in variant_ids) {
            if (_.isEmpty(_.difference(variant_ids[k][1], values)) || variant_ids[k][0] === list_variant_id) {
                $price.html(_priceToStr(variant_ids[k][2]));
                $default_price.html(_priceToStr(variant_ids[k][3]));
                if (variant_ids[k][3]-variant_ids[k][2]>0.01) {
                    $default_price.closest('.oe_website_sale').addClass("discount");
                    $optional_price.closest('.oe_optional').show().css('text-decoration', 'line-through');
                    $default_price.parent().removeClass('d-none');
                } else {
                    $optional_price.closest('.oe_optional').hide();
                    $default_price.parent().addClass('d-none');
                }
                product_id = variant_ids[k][0];
                product_raw_price = variant_ids[k][2];
                display_name = variant_ids[k][4];
                _updateProductImage($(ev.currentTarget).closest('tr.js_product, .oe_website_sale, .o_product_configurator'), product_id, imagesSize);
                break;
            }
        }

        _.each($parent.find("input.js_variant_change:radio, select.js_variant_change"), function (elem) {
            var $input = $(elem);
            var id = +$input.val();
            var values = [id];

            _.each($parent.find("ul:not(:has(input.js_variant_change[value='" + id + "'])) input.js_variant_change:checked, select.js_variant_change"), function (elem) {
                values.push(+$(elem).val());
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
            $product_display_name.val(display_name);
            $product_raw_price.html(product_raw_price);
            $parent.parents('.modal').find('.o_sale_product_configurator_add').removeClass("disabled");

            var $add_to_cart_button = $parent.find("#add_to_cart");
            if(!$add_to_cart_button.hasClass('out_of_stock')){
                $add_to_cart_button.removeClass("disabled");
            }
        } else {
            $parent.addClass("css_not_available");
            $product_id.val(0);
            $product_display_name.val('');
            $parent.find("#add_to_cart").addClass("disabled");
            $parent.parents('.modal').find('.o_sale_product_configurator_add').addClass("disabled");
        }

        computePriceTotal();
    }

    /**
     * Highlight selected color
     */
    function _onChangeColorAttribute (ev) {
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    }

    /**
     * Hack to add and remove from cart with json
     */
    function onClickAddCartJSON (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.closest('.input-group').find("input");
        var product_id = +$input.closest('*:has(input[name="product_id"])').find('input[name="product_id"]').val();
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
        var new_qty = quantity > min ? (quantity < max ? quantity : max) : min;
        // if they are more of one input for this product (eg: option modal)
        $('input[name="'+$input.attr("name")+'"]').add($input).filter(function () {
            var $prod = $(this).closest('*:has(input[name="product_id"])');
            return !$prod.length || +$prod.find('input[name="product_id"]').val() === product_id;
        }).val(new_qty).change();
        return false;
    }

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the pricelist, the price might change when quantity exceeds X
     */
    function onChangeAddQuantity (ev, isWebsite, pricelistId, no_stock_check) {
        var $parent;
        if($(ev.currentTarget).closest('form').length > 0){
            $parent = $(ev.currentTarget).closest('form');
        } else if($(ev.currentTarget).closest('.oe_optional_products_modal').length > 0){
            $parent = $(ev.currentTarget).closest('.oe_optional_products_modal');
        } else {
            $parent = $(ev.currentTarget).closest('.o_product_configurator');
        }

        var qty = $parent.find('input[name="add_qty"]').val();
        var productIDs = [];
        $parent.find(".js_product .js_add_cart_variants").each(function () {
            _.each($(this).data("attribute_value_ids"), function(entry){
                productIDs.push(entry[0]);
            });
        });

        if (productIDs.length) {
            ajax.jsonRpc('/product_configurator/get_unit_price' + (isWebsite ? '_website' : ''), 'call', {
                product_ids: productIDs,
                add_qty: parseInt(qty),
                pricelist_id: pricelistId
            }).then(function (data) {
                $parent.find(".js_product .js_add_cart_variants").each(function () {
                    var currentAttributesData = $(this).data("attribute_value_ids");
                    for (var j = 0 ; j < currentAttributesData.length ; j++) {
                        // update the price of the product (index "2") based on its id (index "0")
                        currentAttributesData[j][2] = data[currentAttributesData[j][0]];
                    }
                    $(this).trigger('change', [no_stock_check]);

                    computePriceTotal();
                });
            });
        }
    }
    
    /**
     * Adds all the necessary events to handle:
     * - Product variant changes
     * - Color changes
     * - Product price based on pricelist and quantity 
     * - Total price
     * ...
     */
    function addConfiguratorEvents ($container, imagesSize, isWebsite, pricelistId) {
        $container
            .find('.css_attribute_color input')
            .change(_onChangeColorAttribute);

        $container
            .find('input.js_variant_change, select.js_variant_change, input.js_product_change, [data-attribute_value_ids]')
            .change(function(ev, no_stock_check){
                onChangeVariant(ev, imagesSize, no_stock_check);
            });

        $container
            .find('input[name="add_qty"]')
            .change(function(ev){
                onChangeAddQuantity(ev, isWebsite, pricelistId);
            });

        $container
            .find('button.js_add_cart_json')
            .click(onClickAddCartJSON);
    }
    
    return {
        addConfiguratorEvents: addConfiguratorEvents,
        onChangeVariant: onChangeVariant,
        onChangeAddQuantity: onChangeAddQuantity,
        onClickAddCartJSON: onClickAddCartJSON,
        computePriceTotal: computePriceTotal
    };
});