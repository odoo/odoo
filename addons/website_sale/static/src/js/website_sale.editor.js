odoo.define('website_sale.add_product', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_product: '_createNewProduct',
    }),

    //----------------------------------------------------------------------
    // Actions
    //----------------------------------------------------------------------

    /**
     * Asks the user information about a new product to create, then creates it
     * and redirects the user to this new page.
     *
     * @private
     * @returns {Deferred} Unresolved if the product is created as there will be
     *                     a redirection
     */
    _createNewProduct: function () {
        var self = this;
        var def = $.Deferred();
        wUtils.prompt({
            id: "editor_new_product",
            window_title: _t("New Product"),
            input: "Product Name",
        }).then(function (name) {
            self._rpc({
                route: '/shop/add_product',
                params: {
                    name: name,
                },
            }).then(function (url) {
                window.location.href = url;
            });
        }, def.resolve.bind(def));
        return def;
    },
});
});

//==============================================================================

odoo.define('website_sale.editor', function (require) {
'use strict';

require('web.dom_ready');
var options = require('web_editor.snippets.options');
var rte = require('web_editor.rte');

if (!$('.js_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.js_sale'");
}

$('.oe_website_sale').on('click', '.oe_currency_value:o_editable', function (ev) {
    $(ev.currentTarget).selectContent();
});

function set_dropzone() {
    var $products = $("#products_grid").find(".oe_product_cart");
    _.each($products, function(product) {
        var $product = $(product);
        if (!$product.find(".oe_drop_zone").length) {
            $product.append($("<div class='oe_drop_zone oe_insert oe_vertical hidden'/>"));
        }
    });
};

options.registry.website_sale = options.Class.extend({
    /**
     * @override
     */
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

        this._rpc({
            model: 'product.style',
            method: 'search_read',
        }).then(function (data) {
            var $ul = self.$el.find('ul[name="style"]');
            for (var k in data) {
                $ul.append(
                    $('<li data-style="'+data[k]['id']+'" data-toggle-class="'+data[k]['html_class']+'" data-no-preview="true"/>')
                        .append( $('<a/>').text(data[k]['name']) ));
            }
            self._setActive();
        });

        set_dropzone();
        this.$overlay.find('.oe_handle.w').removeClass('readonly').addClass('ui-resizable-handle ui-resizable-w');
        this.$overlay.find('.oe_handle.e').removeClass('readonly').addClass('ui-resizable-handle ui-resizable-e');
        this.$overlay.find('.oe_handle.n').removeClass('readonly').addClass('ui-resizable-handle ui-resizable-n');
        this.$overlay.find('.oe_handle.s').removeClass('readonly').addClass('ui-resizable-handle ui-resizable-s');
        this.bind_drag_and_drop_product();
        this.bind_drag_resize_product();
        this.bind_resize();
    },
    reload: function () {
        if (window.location.href.match(/\?enable_editor/)) {
            window.location.reload();
        } else {
            window.location.href = window.location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
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
            self._rpc({
                route: '/shop/change_size',
                params: {
                    id: self.product_tmpl_id,
                    x: x,
                    y: y,
                },
            }).then(self.reload);
        });
    },
    style: function (previewMode, value, $li) {
        this._rpc({
            route: '/shop/change_styles',
            params: {
                id: this.product_tmpl_id,
                style_id: value,
            },
        });
    },
    go_to: function (previewMode, value) {
        var self = this;
        var $product_grid = this.$target.closest("#products_grid");
        this._rpc({
            route: '/shop/change_sequence/' + this.product_tmpl_id,
            params: {
                sequence: value,
            },
        }).then(function(result) {
            $product_grid.find('#product_table').replaceWith(result.template);
            $('.oe_overlay').detach();
            self.rebind_event();
        });
    },
    rebind_event: function(){
        this.rte = new rte.Class(this.editor);
        this.rte.start();
    },
    bind_drag_and_drop_product: function(){
        var self = this;
        var startx, starty, stopx, stopy, direction, target_product_sequence, dragged_product_sequence, target_product_id;
        var is_dragged = false;
        var $product_grid = this.$target.closest("#products_grid");
        this.$target.draggable({
            helper: 'original',
            revert: function() {
                $product_grid.find('div.oe_product_cart[data-publish=on]').children('.oe_drop_zone').addClass('hidden');
                return true;
            },
            revertDuration: 200,
            start: function(event, ui) {
                starty = event.pageY;
                startx = event.pageX;
                var $all_other_published_td = $product_grid.find('div.oe_product_cart[data-publish=on]').not(self.$target.find('div.oe_product_cart'));
                $all_other_published_td.each(function() {
                    var $elem = $(this);
                    $elem.find('.oe_drop_zone').removeClass('hidden').css({'height': $elem.height(), 'width': $elem.width()});
                });
            },
            stop: function(event, ui) {
                stopx = event.pageX;
                stopy = event.pageY;
                direction = (starty > stopy && startx > stopx) ? "up" : "down";
                if (is_dragged) {
                    is_dragged = false;
                    self._rpc({
                        route: '/shop/drag_drop_change_sequence/' + self.product_tmpl_id,
                        params: {
                            sequence: target_product_sequence,
                            direction: direction,
                            dragged_product_sequence: dragged_product_sequence,
                            target_product_id: target_product_id
                        }
                    })
                    .then(function(result) {
                        $product_grid.find("#product_table").replaceWith(result.template);
                        $('.oe_overlay').detach();
                        self.rebind_event();
                    });
                }
            }
        });

        $product_grid.find(".oe_drop_zone").droppable({
            tolerance: 'pointer',
            drop: function(event, ui) {
                is_dragged = true;
                target_product_id = $(this).parents('td').data('id');
                target_product_sequence = $(this).parents('td').data('sequence');
                dragged_product_sequence = self.$target.data('sequence');
            },
        });
    },
    bind_drag_resize_product: function() {
        var self = this;
        var width = this.$target.parents('tr').width()/4;
        var height = this.$target.parents('tr').height();
        var $product_grid = this.$target.closest("#products_grid");
        this.$target.resizable({
            containment: $product_grid.find('#product_table'),
            handles:{n: $(this.$overlay.find('.oe_handle.n')), e: $(this.$overlay.find('.oe_handle.e')), s: $(this.$overlay.find('.oe_handle.s')), w: $(this.$overlay.find('.oe_handle.w'))},
            helper: "ui-resizable-helper",
            grid: [width, height],
            stop: function(event, ui) {
                var colspan = Math.floor(ui.helper[0].clientWidth/Math.floor(width));
                var rowspan = Math.floor(ui.helper[0].clientHeight/Math.floor(height));
                if (colspan !== self.$target.prop("colspan") || rowspan !== self.$target.prop("rowspan")) {
                    self._rpc({
                        route: '/shop/drag_and_drop_resize/' + self.product_tmpl_id,
                        params: {x: colspan, y: rowspan}
                    })
                    .then(function(result) {
                        $product_grid.find('#product_table').replaceWith(result.template);
                        $('.oe_overlay').detach();
                        self.rebind_event();
                    });
                } else {
                    $(this).prop("style", ""); // Bad fix to revert resize, there should be some methodo to revert resize
                }
            }
        });
    },
});
});
