(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        new_product: function() {
            website.prompt({
                id: "editor_new_product",
                window_title: _t("New Product"),
                input: "Product Name",
            }).then(function (name) {
                website.form('/shop/add_product', 'POST', {
                    name: name
                });
            });
        },
    });

    function reload_enable_editor() {
        var search = location.search.replace(/\?|$/, '?enable_editor=1&');
        location.href = location.href.replace(/(\?|#|$).*/, search + location.hash);
    }

    $(document).on('click', '.js_options .js_go_to_top,.js_options .js_go_to_bottom,.js_options .js_go_up,.js_options .js_go_down', function (event) {
        var $a = $(event.currentTarget);
        var $data = $a.parents(".js_options:first");
        var sequence = "top";
        if ($a.hasClass('js_go_to_bottom'))
            sequence = "bottom";
        else if ($a.hasClass('js_go_up'))
            sequence = "up";
        else if ($a.hasClass('js_go_down'))
            sequence = "down";
        openerp.jsonRpc('/shop/change_sequence', 'call', {'id': $data.data('id'), 'sequence': sequence})
            .then(reload_enable_editor);
    });

    $(document).on('click', '.js_options ul[name="style"] a', function (event) {
        var $a = $(event.currentTarget);
        var $li = $a.parent();
        var $data = $a.parents(".js_options:first");
        var $product = $a.parents(".oe_product:first");

        $li.parent().removeClass("active");
        openerp.jsonRpc('/shop/change_styles', 'call', {'id': $data.data('id'), 'style_id': $a.data("id")})
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
        openerp.jsonRpc('/shop/change_size', 'call', {'id': $data.data('id'), 'x': x, 'y': y})
            .then(reload_enable_editor);
    });

})();
