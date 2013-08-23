$(document).ready(function () {
    $(".oe_website_sale input[name='shipping_different']").change(function() {
        $(".oe_website_sale .js_shipping").toggle();
    });

    $(".oe_website_sale .oe_mycart input.js_quantity").change(function() {
        var value = parseInt($(this).val());
        if (!isNaN(value)) {
            window.location.href = window.location.origin + window.location.pathname + 'set_cart/' + $(this).data('id') + '/' + value + '/';
        }
    });
    
});
