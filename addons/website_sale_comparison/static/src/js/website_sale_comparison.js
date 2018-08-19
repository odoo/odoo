odoo.define('website_sale_comparison.comparison', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var Widget = require('web.Widget');
var sAnimations = require('website.content.snippets.animation');
var website_sale_utils = require('website_sale.utils');

var _t = core._t;

var ProductComparison = Widget.extend({
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
            self._updateContent(self.comparelist_product_ids, true);
            if (self.comparelist_product_ids.length) {
                $('.o_product_feature_panel').show();
                self._updateComparelistView();
            }
        });

        $('#comparelist .o_product_panel_header').popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("Compare Products");
            },
            container: '.o_product_feature_panel',
            placement: 'top',
            template: '<div style="width:600px;" class="popover comparator-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>',
            content: function () {
                return $('#comparelist .o_product_panel_content').html();
            }
        });

        $(document.body).on('click.product_comparaison_widget', '.comparator-popover .o_comparelist_products .o_remove', function (ev) {
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
        if (this.comparelist_product_ids.length < this.product_compare_limit) {
            var prod = $elem.data('product-product-id');
            if ($elem.hasClass('o_add_compare_dyn')) {
                prod = $elem.parent().find('.product_id').val();
                if (!prod) { // case List View Variants
                    prod = $elem.parent().find('input:checked').first().val();
                }
                prod = parseInt(prod, 10);
            }
            if (!prod) {
                return;
            }
            this._addNewProducts(prod);
            website_sale_utils.animateClone($('#comparelist .o_product_panel_header'), $elem.closest('form'), -50, 10);
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
        $('.o_product_feature_panel').show();
        if (!_.contains(self.comparelist_product_ids, product_id)) {
            self.comparelist_product_ids.push(product_id);
            if (_.has(self.product_data, product_id)){
                self._updateContent([product_id], false);
            } else {
                self._loadProducts([product_id]).then(function () {
                    self._updateContent([product_id], false);
                });
            }
        }
        self._updateCookie();
    },
    /**
     * @private
     */
    _updateContent: function (product_ids, reset) {
        var self = this;
        if (reset) {
            self.$('.o_comparelist_products .o_product_row').remove();
        }
        _.each(product_ids, function (res) {
            var $template = self.product_data[res].render;
            self.$('.o_comparelist_products').append($template);
        });
        if ($('.comparator-popover').length) {
            $('#comparelist .o_product_panel_header').popover('show');
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
        // force refresh to reposition popover
        this._updateContent(this.comparelist_product_ids, true);
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
        this.$('.o_comparelist_button').hide();
        if (_.isEmpty(this.comparelist_product_ids)) {
            $('.o_product_feature_panel').hide();
            this._togglePanel();
        } else {
            this.$('.o_comparelist_products').show();
            if (this.comparelist_product_ids.length >=2) {
                this.$('.o_comparelist_button').show();
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
