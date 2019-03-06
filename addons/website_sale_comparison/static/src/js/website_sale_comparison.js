odoo.define('website_sale_comparison.comparison', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var Widget = require('web.Widget');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var sAnimations = require('website.content.snippets.animation');
var website_sale_utils = require('website_sale.utils');

var qweb = core.qweb;
var _t = core._t;

// ProductConfiguratorMixin events are overridden on purpose here
// to avoid registering them more than once since they are already registered
// in website_sale.js
var ProductComparison = Widget.extend(ProductConfiguratorMixin, {
    xmlDependencies: ['/website_sale_comparison/static/src/xml/comparison.xml'],

    template: 'product_comparison_template',
    events: {
        'click .o_product_panel_header': '_onClickPanelHeader',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.product_data = {};
        this.comparelist_product_ids = JSON.parse(utils.get_cookie('comparelist_product_ids') || '[]');
        this.product_compare_limit = 4;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        self._loadProducts(this.comparelist_product_ids).then(function () {
            self._updateContent('hide');
        });
        self._updateComparelistView();

        $('#comparelist .o_product_panel_header').popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("Compare Products");
            },
            container: '.o_product_feature_panel',
            placement: 'top',
            template: qweb.render('popover'),
            content: function () {
                return $('#comparelist .o_product_panel_content').html();
            }
        });

        $(document.body).on('click.product_comparaison_widget', '.comparator-popover .o_comparelist_products .o_remove', function (ev) {
            ev.preventDefault();
            self._removeFromComparelist(ev);
        });
        $(document.body).on('click.product_comparaison_widget', '.o_comparelist_remove', function (ev) {
            self._removeFromComparelist(ev);
            var new_link = '/shop/compare/?products=' + self.comparelist_product_ids.toString();
            window.location.href = _.isEmpty(self.comparelist_product_ids) ? '/shop' : new_link;
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(document.body).off('.product_comparaison_widget');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {jQuery} $elem
     */
    handleCompareAddition: function ($elem) {
        var self = this;
        if (this.comparelist_product_ids.length < this.product_compare_limit) {
            var productId = $elem.data('product-product-id');
            if ($elem.hasClass('o_add_compare_dyn')) {
                productId = $elem.parent().find('.product_id').val();
                if (!productId) { // case List View Variants
                    productId = $elem.parent().find('input:checked').first().val();
                }
            }

            var productReady = this.selectOrCreateProduct(
                $elem.closest('form'),
                productId,
                $elem.closest('form').find('.product_template_id').val(),
                false
            );

            productReady.done(function (productId) {
                productId = parseInt(productId, 10);

                if (!productId) {
                    return;
                }

                self._addNewProducts(productId);
                website_sale_utils.animateClone(
                    $('#comparelist .o_product_panel_header'),
                    $elem.closest('form'),
                    -50,
                    10
                );
            });
        } else {
            this.$('.o_comparelist_limit_warning').show();
            $('#comparelist .o_product_panel_header').popover('show');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _loadProducts: function (product_ids) {
        var self = this;
        return this._rpc({
            route: '/shop/get_product_data',
            params: {
                product_ids: product_ids,
                cookies: JSON.parse(utils.get_cookie('comparelist_product_ids') || '[]'),
            },
        }).then(function (data) {
            self.comparelist_product_ids = JSON.parse(data.cookies);
            delete data.cookies;
            _.each(data, function (product) {
                self.product_data[product.product.id] = product;
            });
        });
    },
    /**
     * @private
     */
    _togglePanel: function () {
        $('#comparelist .o_product_panel_header').popover('toggle');
    },
    /**
     * @private
     */
    _addNewProducts: function (product_id) {
        var self = this;
        $('.o_product_feature_panel').addClass('d-md-block');
        if (!_.contains(self.comparelist_product_ids, product_id)) {
            self.comparelist_product_ids.push(product_id);
            if (_.has(self.product_data, product_id)){
                self._updateContent();
            } else {
                self._loadProducts([product_id]).then(function () {
                    self._updateContent();
                });
            }
        }
        self._updateCookie();
    },
    /**
     * @private
     */
    _updateContent: function (force) {
        var self = this;
        this.$('.o_comparelist_products .o_product_row').remove();
        _.each(this.comparelist_product_ids, function (res) {
            var $template = self.product_data[res].render;
            self.$('.o_comparelist_products').append($template);
        });
        if (force !== 'hide' && (this.comparelist_product_ids.length > 1 || force === 'show')) {
            $('#comparelist .o_product_panel_header').popover('show');
        }
        else {
            $('#comparelist .o_product_panel_header').popover('hide');
        }
    },
    /**
     * @private
     */
    _removeFromComparelist: function (e) {
        this.comparelist_product_ids = _.without(this.comparelist_product_ids, $(e.currentTarget).data('product_product_id'));
        $(e.currentTarget).parents('.o_product_row').remove();
        this._updateCookie();
        $('.o_comparelist_limit_warning').hide();
        this._updateContent('show');
    },
    /**
     * @private
     */
    _updateCookie: function () {
        document.cookie = 'comparelist_product_ids=' + JSON.stringify(this.comparelist_product_ids) + '; path=/';
        this._updateComparelistView();
    },
    /**
     * @private
     */
    _updateComparelistView: function () {
        this.$('.o_product_circle').text(this.comparelist_product_ids.length);
        this.$('.o_comparelist_button').removeClass('d-md-block');
        if (_.isEmpty(this.comparelist_product_ids)) {
            $('.o_product_feature_panel').removeClass('d-md-block');
        } else {
            $('.o_product_feature_panel').addClass('d-md-block');
            this.$('.o_comparelist_products').addClass('d-md-block');
            if (this.comparelist_product_ids.length >=2) {
                this.$('.o_comparelist_button').addClass('d-md-block');
                this.$('.o_comparelist_button a').attr('href', '/shop/compare/?products='+this.comparelist_product_ids.toString());
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickPanelHeader: function () {
        this._togglePanel();
    },
});

sAnimations.registry.ProductComparison = sAnimations.Class.extend({
    selector: '.oe_website_sale',
    read_events: {
        'click .o_add_compare, .o_add_compare_dyn': '_onClickAddCompare',
        'click #o_comparelist_table tr': '_onClickComparelistTr',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        this.productComparison = new ProductComparison(this);
        return $.when(def, this.productComparison.appendTo(this.$el));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAddCompare: function (ev) {
        this.productComparison.handleCompareAddition($(ev.currentTarget));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickComparelistTr: function (ev) {
        var $target = $(ev.currentTarget);
        $($target.data('target')).children().slideToggle(100);
        $target.find('.fa-chevron-circle-down, .fa-chevron-circle-right').toggleClass('fa-chevron-circle-down fa-chevron-circle-right');
    },
});
});
