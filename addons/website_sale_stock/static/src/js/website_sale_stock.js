$(document).ready(function () {
    //show warning outofstock, when click on add to cart from shop ,trigger on change of quantity input
    if($('.oe_cart .show_outofstock_warning').length) {
        $('.oe_cart input.js_quantity').trigger('change');
    }
});
