odoo.define('website_sale.product_catalog', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var rpc = require('web.rpc');
var sAnimation = require('website.content.snippets.animation');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var ProductCatalog = Widget.extend({
    template: 'website_sale.product_catalog',
    xmlDependencies: [
        '/website_sale/static/src/xml/website_sale_product_catalog.xml',
        '/website_rating/static/src/xml/website_mail.xml',
    ],
    /**
     * @override
     * @param {Object} options
     */
    init: function (options) {
        this._super.apply(this, arguments);
        this.options = _.pick(options, 'type', 'selection', 'product_ids', 'order', 'x', 'y', 'category_id');
        this.isMobile = config.device.isMobile;
        this.isGrid = this.options.type === 'grid';
        this.size = this.isGrid ? 12 / this.options.x : 12 / (config.device.size_class || 1);
        this.sliderID = _.uniqueId('product-catalog-slider-');
    },
    /**
     * Fetch product catalog details
     *
     * @override
     */
    willStart: function () {
        var self = this;
        var def = rpc.query({
            route: '/get_product_catalog_details',
            params: {
                domain: this._getDomain(),
                order: this._getOrder(),
                limit: this._getLimit(),
            }
        }).then(function (result) {
            self.isRatingActive = result.is_rating_active;
            self.isProductsAvailable = result.is_products_available;
            self.isSalesManager = result.is_sales_manager;
            if (self.options.selection === 'manual') {
                result.products = self._rearrangeManualProducts(result.products);
            }
            self.products = self.isGrid ? result.products : self._getSliderProducts(result.products);
        });
        return $.when(this._super.apply(this, arguments), def);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Group products to display in slider
     *
     * @private
     * @param {Object} products
     * @returns {Array} Contain grouped products
     */
    _getSliderProducts: function (products) {
        var group = _.groupBy(products, function (product, index) {
            return Math.floor(index / (config.device.size_class || 1));
        });
        return _.toArray(group);
    },
    /**
     * @private
     * @returns {Array[]} domain
     */
    _getDomain: function () {
        if (this.options.selection === 'category') {
            return [['public_categ_ids', 'child_of', [this.options.category_id]], ['website_published', '=', true]];
        } else if (this.options.selection === 'manual') {
            return [['id', 'in', this._getManualProductIDs()], ['website_published', '=', true]];
        } else {
            return [['website_published', '=', true]];
        }
    },
    /**
     * @private
     * @returns {string} Order field
     */
    _getOrder: function () {
        var order = {
            price_asc: 'list_price asc',
            price_desc: 'list_price desc',
            name_asc: 'name asc',
            name_desc: 'name desc',
            newest_to_oldest: 'create_date asc',
            oldest_to_newest: 'create_date desc',
        };
        return order[this.options.order];
    },
    /**
     * Number of products to display
     *
     * @private
     * @returns {integer} Limit
     */
    _getLimit: function () {
        return this.isGrid ? this.options.x * this.options.y : 16;
    },
    /**
     * Get manual selected product ids
     *
     * @private
     * @returns {Array} Product ids
     */
    _getManualProductIDs: function () {
        return this.options.product_ids.split(',').map(Number);
    },
    /**
     * Rearrange products for manual selection
     *
     * @private
     * @param {Object} products
     * @returns {Object} Rearranged products
     */
    _rearrangeManualProducts: function (products) {
        var productIDs = this._getManualProductIDs();
        return _.sortBy(products, function (product) {
            return _.indexOf(productIDs, product.id);
        });
    },
});

sAnimation.registry.productCatalog = sAnimation.Class.extend({
    selector: '.s_product_catalog',
    xmlDependencies: [
        '/website_sale/static/src/xml/website_sale_product_catalog.xml'
    ],
    /**
     * @override
     */
    start: function () {
        var $loader = $(QWeb.render('website_sale.product_catalog_loader'));
        this.$el.empty();
        $loader.appendTo(this.$el);
        var productCatalog = new ProductCatalog(this.$el.data()).appendTo(this.$el).then(function () {
                                $loader.remove();
                            });
        return $.when(productCatalog, this._super.apply(this, arguments));
    },
});

return ProductCatalog;

});
