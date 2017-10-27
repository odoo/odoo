odoo.define('website_sale.product_catalog', function (require) {
'use strict';

var ajax = require('web.ajax');
var base = require('web_editor.base');
var core = require('web.core');
var rpc = require('web.rpc');
var website = require('website.website');
var Widget = require('web.Widget');
var utils = require('web.utils');

var QWeb = core.qweb;

ajax.loadXML('/website_sale/static/src/xml/website_sale_product_catalog.xml', QWeb);
ajax.loadXML('/website_rating/static/src/xml/website_mail.xml', QWeb);

var ProductCatalog = Widget.extend({
    template: 'website_sale.product_catalog',
    events: {
        'click .add_to_cart': '_onClickAddToCart',
    },

    /**
     * Initialize all options which are need to render widget.
     * @constructor
     * @override
     * @param {jQuery} $target
     */
    init: function ($target) {
        this._super.apply(this, arguments);
        this.$target = $target;
        this.sizes = {4: 3, 3: 4, 2: 6, 1: 12};
        this.sortBy = {
            'price_asc': {name: 'list_price', asc: true},
            'price_desc': {name: 'list_price', asc: false},
            'name_asc': {name: 'name', asc: true},
            'name_desc': {name: 'name', asc: false},
            'newest_to_oldest': {name: 'create_date', asc: true},
            'oldest_to_newest': {name: 'create_date', asc: false},
            'reorder_products':{}
        };
        this.domains = {
            'all': [],
            'category': ['public_categ_ids', 'child_of', [this.$target.data('catagory-id')]],
            'manual': ['id', 'in', this._getProductIds()]
        };
        this.options = {
            'size': this.sizes[this.$target.data('x')],
            'domain': this.domains[this.$target.data('selection')],
            'sortby': this.sortBy[this.$target.data('sortby')],
            'limit': this.$target.data('x') * this.$target.data('y'),
            'is_rating': false,
            'reorder_ids': ''
        };
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Fetch product details.
     *
     * @override
     * @returns {Deferred}
     */
    willStart: function () {
        var self = this;
        if (_.isEmpty(this.options.sortby)) {
            this.options.domain = ['id', 'in', this._getReOrderIds()];
        }
        var def = rpc.query({
            route: '/get_product_catalog_details',
            params: {
                'domain': this.options.domain,
                'sortby': this.options.sortby,
                'limit': this.options.limit
            }
        }).then(function (result) {
            if (_.isEmpty(self.options.sortby)) {
                self._reOrderingProducts(result);
            }
            self.products = result.products;
            self.options.is_rating = result.is_rating_active;
        });
        return $.when(this._super.apply(this, arguments), def);
    },

    /**
     * If rating option is enable then display rating.
     *
     * @override
     * @returns {Deferred}
     */
    start: function () {
        if (this.options.is_rating) {
            this._renderRating();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * formating currency for the website sale display
     *
     * @private
     * @param {float|false} value that should be formatted.
     * @param {string} currency symbol.
     * @param {string} position should be either before or after.
     * @param {integer} the number of digits that should be used,
     *   instead of the default digits precision in the field.
     * @returns {string} Returns a string representing a float and currency symbol.
     */
    _formatCurrencyValue: function (value, currency_symbol, position, currency_decimal_places) {
        var l10n = core._t.database.parameters;
        value = _.str.sprintf('%.' + currency_decimal_places + 'f', value || 0).split('.');
        value[0] = utils.insert_thousand_seps(value[0]);
        value = value.join(l10n.decimal_point);
        if (position === "after") {
            value += currency_symbol;
        } else {
            value = currency_symbol + value;
        }
        return value;
    },

    /**
     * formating description for the website sale display
     *
     * @private
     * @param {string} get description.
     * @returns {string} Contains string with replace '\n' to '<br>'.
     */
    _formatDescriptionValue: function (description_sale) {
        return description_sale.split("\n").join("<br>");
    },

    /**
     * Get product ids.
     *
     * @private
     * @returns {Array} Contains product ids.
     */
    _getProductIds: function () {
        return _.map(this.$target.find('.product-item'), function(el) {
            return $(el).data('product-id');
        });
    },

    /**
     * Get Re-Order Products Ids.
     *
     * @private
     * @returns {Array} Contains product ids.
     */
    _getReOrderIds: function () {
        if (_.isEmpty(this.options.reorder_ids)) {
            var reorderIDs = this.$target.data('reorder-ids');
            return reorderIDs.indexOf(',') != -1 ? reorderIDs.split(',') : reorderIDs
        } else {
            return this.options.reorder_ids.split(',');
        }
    },

    /**
     * Display rating for each product.
     *
     * @private
     */
    _renderRating: function () {
        var self = this;
        this.$target.find('.product-item').each(function () {
            var productDetails = _.findWhere(self.products, {id: $(this).data('product-id')});
            if (productDetails.product_variant_count >= 1) {
                $(QWeb.render('website_rating.rating_stars_static', {val: productDetails.rating.avg})).appendTo($(this).find('.rating'));
            }
        });
    },

    /**
     * Re-ordering products while selecting re-ordering products option.
     *
     * @private
     * @param {Object} contain products detail
     */
    _reOrderingProducts: function (products) {
        var reorderIDs = this._getReOrderIds();
        _.each(products.products, function (val) {
            reorderIDs[reorderIDs.indexOf(val.id.toString())] = val;
        });
        products['products'] = reorderIDs;
        return products;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the add to cart button is clicked.
     * Add product into cart.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClickAddToCart: function (event) {
        var variantID = $(event.currentTarget).data('product-variant-id');
        website.form('/shop/cart/update', 'POST', {
            product_id: variantID
        });
    },
});

base.ready().then(function () {
    if ($('.s_catalog').length) {
        $('.s_catalog').each(function () {
            var productCatalog = new ProductCatalog($(this));
            $(this).find('.s_no_resize_cols').remove();
            productCatalog.appendTo($(this).find('.container'));
        });
    }
});

return {
    ProductCatalog: ProductCatalog
};

});
