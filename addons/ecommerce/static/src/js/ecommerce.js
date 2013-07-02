$(document).ready(function (){
    $('.oe_ecommerce').on('click', '.btn-success,.btn-primary,.btn-inverse', function (e) {
        var $button = $(e.currentTarget);
        var link = $button.hasClass('btn-inverse') ? '/shop/remove_cart' : '/shop/add_cart';
        // var $add = $button.parent().find('.btn-success,.btn-primary');
        // var $remove = $button.parent().find('.btn-inverse');

        $.get(link, {'product_id': $button.data('id')}, function (quantity) {
            // var quantity = parseInt(quantity);
            // $add.find('.oe_quantity').html(quantity);
            // $add.toggleClass('btn-primary', !quantity).toggleClass('btn-success', !!quantity);
            // $remove.toggleClass('oe_hidden', !quantity);
            // if (!quantity) {
            //     $button.parents('.media:first').remove()
            // }
            window.location.href = window.location.pathname;
        });
    });
});