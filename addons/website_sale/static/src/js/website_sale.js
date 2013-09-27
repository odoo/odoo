$(document).ready(function () {
    $(".oe_website_sale input[name='shipping_different']").change(function () {
        $(".oe_website_sale .js_shipping").toggle();
    });

    $payment = $(".oe_website_sale .js_payment");
    $("input[name='payment_type']", $payment).click(function (ev) {
        var payment_id = $(ev.currentTarget).val();
        $("div[data-id]", $payment).addClass("hidden");
        $("a.btn:last, div[data-id='"+payment_id+"']", $payment).removeClass("hidden");
    });

    // change for css
    $(document).on('mouseup', '.js_publish', function (ev) {
        $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
    });

    function set_my_cart_quantity(qty) {
        $(".my_cart_quantity").html(qty.toString().indexOf(".") > -1 ? qty : qty + '.0').removeClass("hidden");
    }

    $(".oe_website_sale .oe_mycart input.js_quantity").change(function () {
        var $input = $(this);
        var value = parseInt($input.val());
        if (isNaN(value)) value = 0;
        openerp.jsonRpc("/shop/set_cart_json/", 'call', {'order_line_id': $input.data('id'), 'set_number': value})
            .then(function (data) {
                set_my_cart_quantity(data[1]);
                $input.val(data[0]);
                if (!data[0]) {
                    openerp.jsonRpc('/shop/add_cart_json/', 'call', {'order_line_id': $input.data('id')}).then(function (data) {
                        location.reload();
                    });
                }
            });
    });
    
    // hack to add and rome from cart with json
    $('.oe_website_sale a[href*="/add_cart/"], a[href*="/remove_cart/"]').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/shop/add_cart_json/", 'call', {'order_line_id': $link.data('id'), 'remove': $link.is('[href*="/remove_cart/"]')})
            .then(function (data) {
                if (!data[0]) {
                    location.reload();
                }
                set_my_cart_quantity(data[1]);
                $link.parent().find(".js_quantity").val(data[0]);
            });
        return false;
    });

    $(document).on('click', '.js_publish_management .js_go_to_top,.js_publish_management .js_go_to_bottom', function (event) {
        var $a = $(event.currentTarget);
        var $data = $a.parents(".js_publish_management:first");
        openerp.jsonRpc('/shop/change_sequence/', 'call', {'id': $data.data('id'), 'top': $a.hasClass('js_go_to_top')});
    });

    $(document).on('click', '#products_grid .js_options ul[name="style"] a', function (event) {
        var $a = $(event.currentTarget);
        var $li = $a.parent();
        var $data = $a.parents(".js_options:first");
        var $product = $a.parents(".oe_product:first");

        $li.parent().removeClass("active");
        openerp.jsonRpc('/shop/change_styles/', 'call', {'id': $data.data('id'), 'style_id': $a.data("id")})
            .then(function (result) {
                $product.toggleClass($a.data("class"));
                $li.toggleClass("active", result);
            });
    });

    $(document).on('mouseenter', '#products_grid .js_options ul[name="size"] table', function (event) {
        $(event.currentTarget).addClass("oe_hover");
    });
    $(document).on('mouseleave', '#products_grid .js_options ul[name="size"] table', function (event) {
        $(event.currentTarget).removeClass("oe_hover");
    });
    $(document).on('mouseover', '#products_grid .js_options ul[name="size"] td', function (event) {
        var $td = $(event.currentTarget);
        var $table = $td.parents("table:first");
        var x = $td.index()+1;
        var y = $td.parent().index()+1;

        var tr = [];
        for (var yi=0; yi<y; yi++) tr.push("tr:eq("+yi+")");
        var $select_tr = $table.find(tr.join(","));
        var td = [];
        for (var xi=0; xi<x; xi++) td.push("td:eq("+xi+")");
        var $select_td = $select_tr.find(td.join(","));

        $table.find("td").removeClass("select");
        $select_td.addClass("select");
    });
    $(document).on('click', '#products_grid .js_options ul[name="size"] td', function (event) {
        var $td = $(event.currentTarget);
        var $data = $td.parents(".js_options:first");
        var x = $td.index()+1;
        var y = $td.parent().index()+1;
        openerp.jsonRpc('/shop/change_size/', 'call', {'id': $data.data('id'), 'x': x, 'y': y})
            .then(function () {
                location.href =  location.href.replace(/\?|$/, '?') + '&unable_editor=1';
            });
    });

});
