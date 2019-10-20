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

function reload() {
    if (window.location.href.match(/\?enable_editor/)) {
        window.location.reload();
    } else {
        window.location.href = window.location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
    }
}

options.registry.WebsiteSaleGridLayout = options.Class.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],

    /**
     * @override
     */
    start: function () {
        this.ppg = this.$target.closest('[data-ppg]').data('ppg');
        this.ppr = this.$target.closest('[data-ppr]').data('ppr');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        var listLayoutEnabled = this.$target.closest('#products_grid').hasClass('o_wsale_layout_list');
        this.$el.filter('.o_wsale_ppr_submenu').toggleClass('d-none', listLayoutEnabled);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    choosePpg: function (previewMode, value, $opt) {
        var self = this;
        new Dialog(this, {
            title: _t("Choose number of products"),
            $content: $(qweb.render('website_sale.dialog.choosePPG', {widget: this})),
            buttons: [
                {text: _t("Save"), classes: 'btn-primary', click: function () {
                    var $input = this.$('input');
                    var def = self._setPPG($input.val());
                    if (!def) {
                        $input.addClass('is-invalid');
                        return;
                    }
                    return def.then(this.close.bind(this));
                }},
                {text: _t("Discard"), close: true},
            ],
        }).open();
    },
    /**
     * @see this.selectClass for params
     */
    setPpr: function (previewMode, value, $opt) {
        this._rpc({
            route: '/shop/change_ppr',
            params: {
                'ppr': value,
            },
        }).then(reload);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _setActive: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$el.find('[data-set-ppr]')
            .addBack('[data-set-ppr]')
            .removeClass('active')
            .filter(function () {
                var nbColumns = $(this).data('setPpr');
                return nbColumns === self.ppr;
            })
            .addClass('active');
    },
    /**
     * @private
     * @param {integer} ppg
     * @returns {Promise|false}
     */
    _setPPG: function (ppg) {
        ppg = parseInt(ppg);
        if (!ppg || ppg < 1) {
            return false;
        }
        return this._rpc({
            route: '/shop/change_ppg',
            params: {
                'ppg': ppg,
            },
        }).then(reload);
    },
});

options.registry.WebsiteSaleProductsItem = options.Class.extend({
    events: _.extend({}, options.Class.prototype.events || {}, {
        'mouseenter .o_wsale_soptions_menu_sizes table': '_onTableMouseEnter',
        'mouseleave .o_wsale_soptions_menu_sizes table': '_onTableMouseLeave',
        'mouseover .o_wsale_soptions_menu_sizes td': '_onTableItemMouseEnter',
        'click .o_wsale_soptions_menu_sizes td': '_onTableItemClick',
    }),

    /**
     * @override
     */
    start: function () {
        var self = this;

        this.ppr = this.$target.closest('[data-ppr]').data('ppr');
        this.productTemplateID = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));

        var defs = [this._super.apply(this, arguments)];

        defs.push(this._rpc({
            model: 'product.style',
            method: 'search_read',
        }).then(function (data) {
            var $ul = self.$el.find('[name="style"]');
            for (var k in data) {
                $ul.append(
                    $('<we-button data-style="' + data[k]['id'] + '" data-toggle-class="' + data[k]['html_class'] + '"/>')
                        .append(data[k]['name'])
                );
            }
            self._setActive();
        }));

        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    onFocus: function () {
        var listLayoutEnabled = this.$target.closest('#products_grid').hasClass('o_wsale_layout_list');
        this.$el.find('.o_wsale_soptions_menu_sizes').closest('we-collapse-area')
            .toggleClass('d-none', listLayoutEnabled);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    style: function (previewMode, value, $opt) {
        this._rpc({
            route: '/shop/change_styles',
            params: {
                'id': this.productTemplateID,
                'style_id': value,
            },
        });
    },
    /**
     * @see this.selectClass for params
     */
    changeSequence: function (previewMode, value, $opt) {
        this._rpc({
            route: '/shop/change_sequence',
            params: {
                id: this.productTemplateID,
                sequence: value,
            },
        }).then(reload);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _setActive: function () {
        var sizeX = parseInt(this.$target.attr('colspan') || 1);
        var sizeY = parseInt(this.$target.attr('rowspan') || 1);

        var $size = this.$el.find('.o_wsale_soptions_menu_sizes');
        $size.find('tr:nth-child(-n + ' + sizeY + ') td:nth-child(-n + ' + sizeX + ')')
             .addClass('selected');

        // Adapt size array preview to fit ppr
        $size.find('tr td:nth-child(n + ' + parseInt(this.ppr + 1) + ')').hide();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onTableMouseEnter: function (ev) {
        $(ev.currentTarget).addClass('oe_hover');
    },
    /**
     * @private
     */
    _onTableMouseLeave: function (ev) {
        $(ev.currentTarget).removeClass('oe_hover');
    },
    /**
     * @private
     */
    _onTableItemMouseEnter: function (ev) {
        var $td = $(ev.currentTarget);
        var $table = $td.closest("table");
        var x = $td.index()+1;
        var y = $td.parent().index()+1;

        var tr = [];
        for (var yi = 0; yi < y; yi++) {
            tr.push("tr:eq(" + yi + ")");
        }
        var $selectTr = $table.find(tr.join(","));
        var td = [];
        for (var xi = 0; xi < x; xi++) {
            td.push("td:eq(" + xi + ")");
        }
        var $selectTd = $selectTr.find(td.join(","));

        $table.find("td").removeClass("select");
        $selectTd.addClass("select");
    },
    /**
     * @private
     */
    _onTableItemClick: function (ev) {
        var $td = $(ev.currentTarget);
        var x = $td.index() + 1;
        var y = $td.parent().index() + 1;
        this._rpc({
            route: '/shop/change_size',
            params: {
                id: this.productTemplateID,
                x: x,
                y: y,
            },
        }).then(reload);
    },
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

/**
 * Handles the edition of products search bar snippet.
 */
options.registry.ProductsRecentlyViewed = options.Class.extend({}); // TODO remove me in master
});
