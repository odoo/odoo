odoo.define('website_sale_options.website_sale', function (require) {
'use strict';

var weContext = require('web_editor.context');
var sAnimations = require('website.content.snippets.animation');
require('website_sale.website_sale');

sAnimations.registry.WebsiteSale.include({
    /**
     * @override
     */
    _onClickSubmit: function (ev) {
        if ($(ev.currentTarget).is('#add_to_cart, #products_grid .a-submit')) {
            return;
        }
        this._super.apply(this, arguments);
    },
});

sAnimations.registry.WebsiteSaleOptions = sAnimations.Class.extend({
    selector: '.oe_website_sale',
    read_events: {
        'click #add_to_cart, #products_grid .a-submit': '_onClickAdd',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._handleAdd = _.debounce(this._handleAdd.bind(this), 200, true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _handleAdd: function ($form) {
        var quantity = parseFloat($form.find('input[name="add_qty"]').val() || 1);
        var product_id = parseInt($form.find('input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked').first().val(),10);
        this._rpc({
            route: '/shop/modal',
            params: {
                product_id: product_id,
                kwargs: {
                   context: _.extend({'quantity': quantity}, weContext.get()),
                },
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

            $modal.on('click', '.a-submit', function (ev) {
                var $a = $(this);
                $form.ajaxSubmit({
                    url:  '/shop/cart/update_option',
                    data: {lang: weContext.get().lang},
                    success: function (quantity) {
                        if (!$a.hasClass('js_goto_shop')) {
                            window.location.pathname = window.location.pathname.replace(/shop([\/?].*)?$/, "shop/cart");
                        }
                        var $q = $(".my_cart_quantity");
                        $q.parent().parent().removeClass("d-none", !quantity);
                        $q.html(quantity).hide().fadeIn(600);
                    }
                });
                $modal.modal('hide');
                ev.preventDefault();
            });

            $modal.on('click', '.css_attribute_color input', function (ev) {
                $modal.find('.css_attribute_color').removeClass("active");
                $modal.find('.css_attribute_color:has(input:checked)').addClass("active");
            });

            $modal.on("click", "a.js_add, a.js_remove", function (ev) {
                ev.preventDefault();
                var $parent = $(this).parents('.js_product:first');
                $parent.find("a.js_add, span.js_remove").toggleClass('d-none');
                $parent.find("input.js_optional_same_quantity").val( $(this).hasClass("js_add") ? 1 : 0 );
                $parent.find(".js_remove");
            });

            $modal.on("change", "input.js_quantity", function () {
                var qty = parseFloat($(this).val());
                if (qty === 1) {
                    $(".js_remove .js_items").addClass('d-none');
                    $(".js_remove .js_item").removeClass('d-none');
                } else {
                    $(".js_remove .js_items").removeClass('d-none').text($(".js_remove .js_items:first").text().replace(/[0-9.,]+/, qty));
                    $(".js_remove .js_item").addClass('d-none');
                }
            });

            $modal.find('input[name="add_qty"]').val(quantity).change();
            $('.js_add_cart_variants').each(function () {
                $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
                });

                $modal.on("change", 'input[name="add_qty"]', function (ev) {
                    var product_id = $($modal.find('span.oe_price[data-product-id]')).first().data('product-id');
                    var product_ids = [product_id];
                    var $products_dom = [];
                    $("ul.js_add_cart_variants[data-attribute_value_ids]").each(function () {
                        var $el = $(this);
                        $products_dom.push($el);
                        _.each($el.data("attribute_value_ids"), function (values) {
                            product_ids.push(values[0]);
                        });
                    });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickAdd: function (ev) {
        ev.preventDefault();
        var $form = $(ev.currentTarget).closest('form');
        this._handleAdd($form);
    },
});
});
