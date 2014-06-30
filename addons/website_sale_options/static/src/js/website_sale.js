$(document).ready(function () {
    $('.oe_website_sale #add_to_cart, .oe_website_sale #products_grid .a-submit')
        .off('click')
        .removeClass('a-submit')
        .click(function (event) {
            var $form = $(this).closest('form');
            var quantity = parseFloat($form.find('input[name="add_qty"]').val() || 1);
            event.preventDefault();
            openerp.jsonRpc("/shop/modal", 'call', {
                    'product_id': parseInt($form.find('input[name="product_id"]').val(),10),
                    kwargs: {
                       context: openerp.website.get_context()
                    },
                }).then(function (modal) {
                    var $modal = $(modal);

                    $modal.appendTo($form)
                        .modal()
                        .on('hidden.bs.modal', function () {
                            $(this).remove();
                        });

                    $modal.on('click', '.a-submit', function () {
                        var $a = $(this);
                        $form.ajaxSubmit({
                            url:  '/shop/cart/update_option',
                            success: function (quantity) {
                                if (!$a.hasClass('js_goto_shop')) {
                                    window.location.href = window.location.href.replace(/shop([\/?].*)?$/, "shop/cart");
                                }
                                var $q = $(".my_cart_quantity");
                                $q.parent().parent().removeClass("hidden", !quantity);
                                $q.html(quantity).hide().fadeIn(600);
                            }
                        });
                        $modal.modal('hide');
                    });

                    $modal.on("click", "a.js_add, a.js_remove", function (event) {
                        event.preventDefault();
                        var $parent = $(this).parents('.js_product:first');
                        $parent.find("a.js_add, span.js_remove").toggleClass("hidden");
                        $parent.find("input.js_optional_same_quantity").val( $(this).hasClass("js_add") ? 1 : 0 );
                        var $remove = $parent.find(".js_remove");
                    });

                    $modal.on("change", "input.js_quantity", function (event) {
                        var qty = parseFloat($(this).val());
                        if (qty === 1) {
                            $(".js_remove .js_items").addClass("hidden");
                            $(".js_remove .js_item").removeClass("hidden");
                        } else {
                            $(".js_remove .js_items").removeClass("hidden").text($(".js_remove .js_items").text().replace(/[0-9.,]+/, qty));
                            $(".js_remove .js_item").addClass("hidden");
                        }
                    });

                    $modal.find('input[name="add_qty"]').val(quantity).change();
                    $('ul.js_add_cart_variants').each(function () {
                        $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
                    });
                });
            return false;
        });

});
