odoo.define('website_sale.s_products_searchbar', function (require) {
'use strict';

const concurrency = require('web.concurrency');
const publicWidget = require('web.public.widget');

const { qweb } = require('web.core');

/**
 * @todo maybe the custom autocomplete logic could be extract to be reusable
 */
publicWidget.registry.productsSearchBar = publicWidget.Widget.extend({
    selector: '.o_wsale_products_searchbar_form',
    xmlDependencies: ['/website_sale/static/src/xml/website_sale_utils.xml'],
    events: {
        'input .search-query': '_onInput',
        'focusout': '_onFocusOut',
        'keydown .search-query': '_onKeydown',
    },
    autocompleteMinWidth: 300,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._dp = new concurrency.DropPrevious();

        this._onInput = _.debounce(this._onInput, 400);
        this._onFocusOut = _.debounce(this._onFocusOut, 100);
    },
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('.search-query');

        this.order = this.$('.o_wsale_search_order_by').val();
        this.limit = parseInt(this.$input.data('limit'));
        this.displayDescription = !!this.$input.data('displayDescription');
        this.displayPrice = !!this.$input.data('displayPrice');
        this.displayImage = !!this.$input.data('displayImage');

        if (this.limit) {
            this.$input.attr('autocomplete', 'off');
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _fetch: function () {
        return this._rpc({
            route: '/shop/products/autocomplete',
            params: {
                'term': this.$input.val(),
                'options': {
                    'order': this.order,
                    'limit': this.limit,
                    'display_description': this.displayDescription,
                    'display_price': this.displayPrice,
                    'max_nb_chars': Math.round(Math.max(this.autocompleteMinWidth, parseInt(this.$el.width())) * 0.22),
                },
            },
        });
    },
    /**
     * @private
     */
    _render: function (res) {
        var $prevMenu = this.$menu;
        this.$el.toggleClass('dropdown show', !!res);
        if (res) {
            var products = res['products'];
            this.$menu = $(qweb.render('website_sale.productsSearchBar.autocomplete', {
                products: products,
                hasMoreProducts: products.length < res['products_count'],
                currency: res['currency'],
                widget: this,
            }));
            this.$menu.css('min-width', this.autocompleteMinWidth);
            this.$el.append(this.$menu);
        }
        if ($prevMenu) {
            $prevMenu.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInput: function () {
        if (!this.limit) {
            return;
        }
        this._dp.add(this._fetch()).then(this._render.bind(this));
    },
    /**
     * @private
     */
    _onFocusOut: function () {
        if (!this.$el.has(document.activeElement).length) {
            this._render();
        }
    },
    /**
     * @private
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ESCAPE:
                this._render();
                break;
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                ev.preventDefault();
                if (this.$menu) {
                    let $element = ev.which === $.ui.keyCode.UP ? this.$menu.children().last() : this.$menu.children().first();
                    $element.focus();
                }
                break;
        }
    },
});
});
