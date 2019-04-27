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

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new product to create, then creates it
     * and redirects the user to this new product.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewProduct: function () {
        var self = this;
        return wUtils.prompt({
            id: "editor_new_product",
            window_title: _t("New Product"),
            input: _t("Name"),
        }).then(function (result) {
            if (!result.val) {
                return;
            }
            return self._rpc({
                route: '/shop/add_product',
                params: {
                    name: result.val,
                },
            }).then(function (url) {
                window.location.href = url;
                return new Promise(function () {});
            });
        });
    },
});
});

//==============================================================================

odoo.define('website_sale.editor', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var publicWidget = require('web.public.widget');

var _t = core._t;
var qweb = core.qweb;

publicWidget.registry.websiteSaleCurrency = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    disabledInEditableMode: false,
    edit_events: {
        'click .oe_currency_value:o_editable': '_onCurrencyValueClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCurrencyValueClick: function (ev) {
        $(ev.currentTarget).selectContent();
    },
});

options.registry.website_sale = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.product_tmpl_id = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));

        var size_x = parseInt(this.$target.attr("colspan") || 1);
        var size_y = parseInt(this.$target.attr("rowspan") || 1);

        var $size = this.$el.find('div[name="size"]');
        var $select = $size.find('tr:eq(0) td:lt('+size_x+')');
        if (size_y >= 2) $select = $select.add($size.find('tr:eq(1) td:lt('+size_x+')'));
        if (size_y >= 3) $select = $select.add($size.find('tr:eq(2) td:lt('+size_x+')'));
        if (size_y >= 4) $select = $select.add($size.find('tr:eq(3) td:lt('+size_x+')'));
        $select.addClass("selected");

        this._rpc({
            model: 'product.style',
            method: 'search_read',
        }).then(function (data) {
            var $ul = self.$el.find('div[name="style"]');
            for (var k in data) {
                $ul.append(
                    $('<a class="dropdown-item" role="menuitem" data-style="'+data[k]['id']+'" data-toggle-class="'+data[k]['html_class']+'" data-no-preview="true"/>')
                        .append(data[k]['name']));
            }
            self._setActive();
        });

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
        this.$el.on('mouseenter', 'div[name="size"] table', function (event) {
            $(event.currentTarget).addClass("oe_hover");
        });
        this.$el.on('mouseleave', 'div[name="size"] table', function (event) {
            $(event.currentTarget).removeClass("oe_hover");
        });
        this.$el.on('mouseover', 'div[name="size"] td', function (event) {
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
        this.$el.on('click', 'div[name="size"] td', function (event) {
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
        this._rpc({
            route: '/shop/change_sequence',
            params: {
                id: this.product_tmpl_id,
                sequence: value,
            },
        }).then(this.reload);
    }
});

/**
 * Handles the edition of products search bar snippet.
 */
options.registry.ProductsSearchBar = options.Class.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],

    /**
     * @override
     */
    start: function () {
        this.$searchProductsInput = this.$('.search-query');
        this.$searchOrderField = this.$('.o_wsale_search_order_by');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    openSearchbarSettings: function (previewMode, value, $opt) {
        var self = this;
        new Dialog(this, {
            title: _t("Products Search Bar"),
            $content: $(qweb.render('website_sale.dialog.productsSearchBar', {
                currentOrderBy: this.$searchOrderField.val(),
                currentLimit: parseInt(this.$searchProductsInput.attr('data-limit')),
                currentDisplayDescription: this.$searchProductsInput.attr('data-display-description') === 'true',
                currentDisplayPrice: this.$searchProductsInput.attr('data-display-price') === 'true',
                currentDisplayImage: this.$searchProductsInput.attr('data-display-image') === 'true',
            })),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    click: function () {
                        self.$searchOrderField.attr({
                            'value': this.$('#order_by').val(),
                        });
                        self.$searchProductsInput.attr({
                            'data-limit': this.$('#use_autocomplete').is(':checked') ? this.$('#limit').val() : 0,
                            'data-display-description': this.$('#display_description').is(':checked'),
                            'data-display-price': this.$('#display_price').is(':checked'),
                            'data-display-image': this.$('#display_image').is(':checked'),
                        });
                        self.$target.trigger('content_changed');
                        this.close();
                    },
                },
                {
                    text: _t("Discard"),
                    close: true,
                },
            ],
        }).open();
    },
});
});
