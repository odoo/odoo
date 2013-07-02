$(document).ready(function (){
    $('.oe_ecommerce').on('click', '.oe_product .btn-success,.oe_product .btn-primary,.btn-inverse', function (e) {
        var mycart = !!$('.oe_ecommerce .oe_mycart').size();
        var $button = $(e.currentTarget);
        var link = $button.hasClass('btn-inverse') ? '/shop/remove_cart' : '/shop/add_cart';
        var $add = $button.parent().find('.btn-success,.btn-primary');
        var $remove = $button.parent().find('.btn-inverse');

        $.get(link, {'product_id': $button.data('id')}, function (result) {
            var result = JSON.parse(result);
            var quantity = parseInt(result.quantity);
            $add.find('.oe_quantity').html(quantity);
            $add.toggleClass('btn-primary', !quantity).toggleClass('btn-success', !!quantity);
            $remove.toggleClass('oe_hidden', !quantity);
            if (mycart && !quantity) {
                $button.parents('.oe_product:first').remove()
            }
            $('.oe_ecommerce .oe_total').replaceWith(''+result.totalHTML);
        });
    });
});