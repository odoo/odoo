odoo.define('website_sale_options.website_sale', function(require) {
"use strict";

var ajax = require('web.ajax');
var website = require('website.website');
var base = require('web_editor.base');
require('website_sale.website_sale');

$('.oe_website_sale #add_to_cart, .oe_website_sale #products_grid .a-submit')
    .off('click')
    .removeClass('a-submit')
    .click(_.debounce(function (event) {
        var $form = $(this).closest('form');
        var quantity = parseFloat($form.find('input[name="add_qty"]').val() || 1);
        var product_id = parseInt($form.find('input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked').first().val(),10);
        event.preventDefault();
        ajax.jsonRpc("/shop/modal", 'call', {
                'product_id': product_id,
                'kwargs': {
                   'context': _.extend({'quantity': quantity}, base.get_context())
                },
            }).then(function (modal) {
                var $modal = $(modal);

                $modal.find('img:first').attr("src", "/web/image/product.product/" + product_id + "/image_medium");

                // disable opacity on the <form> if currently active (in case the product is
                // not published), as it interferes with bs modals
                $form.addClass('css_options');

                $modal.appendTo($form)
                    .modal()
                    .on('hidden.bs.modal', function () {
                        $form.removeClass('css_options'); // possibly reactivate opacity (see above)
                        $(this).remove();
                    });

                $modal.on('click', '.a-submit', function () {
                    var $a = $(this);
                    $form.ajaxSubmit({
                        url:  '/shop/cart/update_option',
                        data: {lang: base.get_context().lang},
                        success: function (quantity) {
                            if (!$a.hasClass('js_goto_shop')) {
                                window.location.pathname = window.location.pathname.replace(/shop([\/?].*)?$/, "shop/cart");
                            }
                            var $q = $(".my_cart_quantity");
                            $q.parent().parent().removeClass("hidden", !quantity);
                            $q.html(quantity).hide().fadeIn(600);
                        }
                    });
                    $modal.modal('hide');
                });

                $modal.on('click', '.css_attribute_color input', function (event) {
                    $modal.find('.css_attribute_color').removeClass("active");
                    $modal.find('.css_attribute_color:has(input:checked)').addClass("active");
                });

                $modal.on("click", "a.js_add, a.js_remove", function (event) {
                    event.preventDefault();
                    var $parent = $(this).parents('.js_product:first');
                    $parent.find("a.js_add, span.js_remove").toggleClass("hidden");
                    $parent.find("input.js_optional_same_quantity").val( $(this).hasClass("js_add") ? 1 : 0 );
                    $parent.find(".js_remove");
                });

                $modal.on("change", "input.js_quantity", function () {
                    var qty = parseFloat($(this).val());
                    if (qty === 1) {
                        $(".js_remove .js_items").addClass("hidden");
                        $(".js_remove .js_item").removeClass("hidden");
                    } else {
                        $(".js_remove .js_items").removeClass("hidden").text($(".js_remove .js_items:first").text().replace(/[0-9.,]+/, qty));
                        $(".js_remove .js_item").addClass("hidden");
                    }
                });

                $modal.find('input[name="add_qty"]').val(quantity).change();
                $('.js_add_cart_variants').each(function () {
                    $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
                    });

                    $modal.on("change", 'input[name="add_qty"]', function (event) {
                        var product_id = $($modal.find('span.oe_price[data-product-id]')).first().data('product-id');
                        var product_ids = [product_id];
                        var $products_dom = [];
                        $("ul.js_add_cart_variants[data-attribute_value_ids]").each(function(){
                            var $el = $(this);
                            $products_dom.push($el);
                            _.each($el.data("attribute_value_ids"), function (values) {
                                product_ids.push(values[0]);
                            });
                        });
                });
            });
        return false;
    }, 200, true));

});
