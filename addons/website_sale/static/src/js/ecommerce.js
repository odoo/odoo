$(document).ready(function () {
    $('.oe_ecommerce').on('click', '.oe_product .btn, .oe_product_detail .btn', function (e) {
        var $button = $(e.currentTarget);
        var $product = $button.parents('.oe_product:first, .oe_product_detail:first');
        var link = $button.hasClass('btn-inverse') ? '/shop/remove_cart' : '/shop/add_cart';
        var $add = $product.find('.btn-success,.btn-primary');
        var $remove = $product.find('.btn-inverse');

        $.get(link, {'product_id': $button.data('id')}, function (result) {
            var result = JSON.parse(result);
            var quantity = parseInt(result.quantity);
            $add.find('.oe_quantity')
                .html(quantity);
            $add.toggleClass('btn-primary', !quantity)
                .toggleClass('btn-success', !!quantity);
            $remove.toggleClass('oe_hidden', !quantity);
            if ($('.oe_mycart').size() && !quantity) {
                $product.remove()
            }
            $('.oe_ecommerce .oe_total').replaceWith(''+result.totalHTML);
        });
    });


    var $checkout = $(".oe_ecommerce .oe_checkout");
    $(".oe_ecommerce input[name='shipping_different']").change(function() {
        $(".oe_ecommerce .js_shipping").toggle();
    });
    $(".oe_ecommerce .js_error_payment").click(function(e) {
        var values = {};
        $checkout.find(".js_inputs:not(:hidden) input:not(:checkbox), .js_signin_modal input").each(function() {
            values[$(this).attr("name")] = $(this).val();
        });
        $checkout.find("input").css("border", "");
        $.post('/shop/confirm_order', values, function (result) {
            var result = JSON.parse(result);
            if (result.error.length) {
                $inputs = $checkout.find("input[name='" + result.error.join("'], input[name='") + "']");
                $inputs.css("border", "1px solid #dd0000");
                $inputs.first().focus();
            } else {
                var $form = $(e.currentTarget).parent().find("input[name='submit']").click();
            }
        });
    });
});