$(document).ready(function () {

    $('#add_to_cart').click(function (event) {
        event.preventDefault();
        openerp.jsonRpc("/shop/cart/update_json", 'call', {
            'line_id': parseInt($input.data('line-id'),10),
            'product_id': parseInt($input.data('product-id'),10),
            'set_qty': value})
            .then(function (data) {
                if (!data.quantity) {
                    location.reload();
                    return;
                }
                if (data.option_ids.length) {
                    _.each(data.option_ids, function (line_id) {
                        $(".js_quantity[data-line-id="+line_id+"]").text(data.quantity);
                    });
                }
                var $q = $(".my_cart_quantity");
                $q.parent().parent().removeClass("hidden", !data.quantity);
                $q.html(data.cart_quantity).hide().fadeIn(600);
                $input.val(data.quantity);
                $("#cart_total").replaceWith(data['website_sale.total']);
            });
        return false;
    });

    $('form:has(#add_to_cart)').submit(function (event) {
        event.preventDefault();
        $(this).ajaxSubmit({
            beforeSubmit:  function () { console.log("beforeSubmit"); },
            success:       function () { console.log("success"); },
            url:           '/stqdfdsfdf'
        });
        return false;
    });

});
