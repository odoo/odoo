odoo.define('website_sale.editor', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Model = require('web.Model');
var contentMenu = require('website.contentMenu');
var options = require('web_editor.snippets.options');

var website = require('website.website');

var _t = core._t;

contentMenu.TopBar.include({
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

if(!$('.js_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.js_sale'");
}

options.registry.website_sale = options.Class.extend({
    start: function () {
        var self = this;
        this.product_tmpl_id = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));

        var size_x = parseInt(this.$target.attr("colspan") || 1);
        var size_y = parseInt(this.$target.attr("rowspan") || 1);

        var $size = this.$el.find('ul[name="size"]');
        var $select = $size.find('tr:eq(0) td:lt('+size_x+')');
        if (size_y >= 2) $select = $select.add($size.find('tr:eq(1) td:lt('+size_x+')'));
        if (size_y >= 3) $select = $select.add($size.find('tr:eq(2) td:lt('+size_x+')'));
        if (size_y >= 4) $select = $select.add($size.find('tr:eq(3) td:lt('+size_x+')'));
        $select.addClass("selected");

        new Model('product.style')
            .call('search_read', [[]])
                .then(function (data) {
                    var $ul = self.$el.find('ul[name="style"]');
                    for (var k in data) {
                        $ul.append(
                            $('<li data-style="'+data[k]['id']+'" data-toggle_class="'+data[k]['html_class']+'"/>')
                                .append( $('<a/>').text(data[k]['name']) ));
                    }
                    self.set_active();
                });

        this.bind_resize();
    },
    reload: function () {
        if (location.href.match(/\?enable_editor/)) {
            location.reload();
        } else {
            location.href = location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
        }
    },
    bind_resize: function () {
        var self = this;
        this.$el.on('mouseenter', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).addClass("oe_hover");
        });
        this.$el.on('mouseleave', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).removeClass("oe_hover");
        });
        this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
            var $td = $(event.currentTarget);
            var $table = $td.closest("table");
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
        this.$el.on('click', 'ul[name="size"] td', function (event) {
            var $td = $(event.currentTarget);
            var x = $td.index()+1;
            var y = $td.parent().index()+1;
            ajax.jsonRpc('/shop/change_size', 'call', {'id': self.product_tmpl_id, 'x': x, 'y': y})
                .then(self.reload);
        });
    },
    style: function (type, value, $li) {
        if(type !== "click") return;
        ajax.jsonRpc('/shop/change_styles', 'call', {'id': this.product_tmpl_id, 'style_id': value});
    },
    go_to: function (type, value) {
        if(type !== "click") return;
        ajax.jsonRpc('/shop/change_sequence', 'call', {'id': this.product_tmpl_id, 'sequence': value})
            .then(this.reload);
    }
});

});
