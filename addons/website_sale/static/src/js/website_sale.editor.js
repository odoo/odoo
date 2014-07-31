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

    website.snippet.options.website_sale = website.snippet.Option.extend({
        start: function () {
            this.product_tmpl_id = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));

            var size_x = parseInt(this.$target.attr("colspan") || 1);
            var size_y = parseInt(this.$target.attr("rowspan") || 1);

            var $size = this.$el.find('ul[name="size"]');
            var $select = $size.find('tr:eq(0) td:lt('+size_x+')');
            if (size_y >= 2) $select = $select.add($size.find('tr:eq(1) td:lt('+size_x+')'));
            if (size_y >= 3) $select = $select.add($size.find('tr:eq(2) td:lt('+size_x+')'));
            if (size_y >= 4) $select = $select.add($size.find('tr:eq(3) td:lt('+size_x+')'));
            $select.addClass("selected");

            website.session.model('product.template')
                .call('read', [[this.product_tmpl_id], ['website_style_ids']])
                .then(function (data) {
                    console.log(data);
                });

            this.bind_resize();
        },
        reload: function () {
            var search = location.search.replace(/\?|$/, '?enable_editor=1&');
            location.href = location.href.replace(/(\?|#|$).*/, search + location.hash);
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
                var $data = $td.closest(".js_options:first");
                var x = $td.index()+1;
                var y = $td.parent().index()+1;
                openerp.jsonRpc('/shop/change_size', 'call', {'id': self.product_tmpl_id, 'x': x, 'y': y})
                    .then(self.reload);
            });
        },
        style: function (type, value) {
            if(type !== "click") return;
            var self = this;
            openerp.jsonRpc('/shop/change_styles', 'call', {'id': this.product_tmpl_id, 'style_id': value})
                .then(function (result) {
                    self.$target.toggleClass($a.data("class"));
                });
        },
        go_to: function (type, value) {
            if(type !== "click") return;
            openerp.jsonRpc('/shop/change_sequence', 'call', {'id': this.product_tmpl_id, 'sequence': value})
                .then(self.reload);
        }
    });

})();
