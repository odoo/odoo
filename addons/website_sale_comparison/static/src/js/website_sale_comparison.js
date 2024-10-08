/** @odoo-module **/

import { Mutex } from "@web/core/utils/concurrency";
import publicWidget from "@web/legacy/js/public/public_widget";
import { cookie } from "@web/core/browser/cookie";;
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import website_sale_utils from "@website_sale/js/website_sale_utils";
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";

const cartHandlerMixin = website_sale_utils.cartHandlerMixin;

// VariantMixin events are overridden on purpose here
// to avoid registering them more than once since they are already registered
// in website_sale.js
var ProductComparison = publicWidget.Widget.extend(VariantMixin, {
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
        this.comparelist_product_ids = JSON.parse(cookie.get('comparelist_product_ids') || '[]');
        this.product_compare_limit = 4;
        this.guard = new Mutex();
        this.rpc = this.bindService("rpc");
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
            template: renderToString('popover'),
            content: function () {
                return $('#comparelist .o_product_panel_content').html();
            }
        });
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        $(window).trigger('resize');

        $(document.body).on('click.product_comparaison_widget', '.comparator-popover .o_comparelist_products .o_remove', function (ev) {
            ev.preventDefault();
            self._removeFromComparelist(ev);
        });
        $(document.body).on('click.product_comparaison_widget', '.o_comparelist_remove', function (ev) {
            self._removeFromComparelist(ev);
            self.guard.exec(function() {
                const newLink = '/shop/compare?products=' + encodeURIComponent(self.comparelist_product_ids);
                window.location.href = Object.keys(self.comparelist_product_ids || {}).length === 0 ? '/shop' : newLink;
            });
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

            let $form = $elem.closest('form');
            $form = $form.length ? $form : $('#product_details > form');
            this.selectOrCreateProduct(
                $form,
                productId,
                $form.find('.product_template_id').val(),
                false
            ).then(function (productId) {
                productId = parseInt(productId, 10) || parseInt($elem.data('product-product-id'), 10);
                if (!productId) {
                    return;
                }
                // Made changes based on `_hideBottomFixedElements` logic:
                // bottom-fixed elements (e.g. compare list button) get
                // hidden if overlapped by modals. In our case, the cookie
                // modal was hiding it. To avoid the compare button animating
                // to the top-left, we now ensure it stays visible when an
                // item is added to the compare list.
                self.el.classList.remove("o_bottom_fixed_element_hidden");
                self._addNewProducts(productId).then(function () {
                    website_sale_utils.animateClone(
                        $('#comparelist .o_product_panel_header'),
                        $elem.closest('form'),
                        -50,
                        10
                    );
                });
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
        return this.rpc('/shop/get_product_data', {
            product_ids: product_ids,
            cookies: JSON.parse(cookie.get('comparelist_product_ids') || '[]'),
        }).then(function (data) {
            self.comparelist_product_ids = JSON.parse(data.cookies);
            delete data.cookies;
            Object.values(data).forEach((product) => {
                self.product_data[product.product.id] = product;
            });
            if (product_ids.length > Object.keys(data).length) {
                /* If some products have been archived
                they are not displayed but the count & cookie
                need to be updated.
                */
                self._updateCookie();
            }
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
        return this.guard.exec(this._addNewProductsImpl.bind(this, product_id));
    },
    _addNewProductsImpl: function (product_id) {
        var self = this;
        $('.o_product_feature_panel').addClass('d-md-block');
        if (!self.comparelist_product_ids.includes(product_id)) {
            self.comparelist_product_ids.push(product_id);
            if (Object.prototype.hasOwnProperty.call(self.product_data, product_id)) {
                self._updateContent();
            } else {
                return self._loadProducts([product_id]).then(function () {
                    self._updateContent();
                    self._updateCookie();
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
        this.comparelist_product_ids.forEach((res) => {
            if (self.product_data.hasOwnProperty(res)) {
                // It is possible that we do not have the required product_data for all IDs in
                // comparelist_product_ids
                var $template = self.product_data[res].render;
                self.$('.o_comparelist_products').append($template);
            }
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
        this.guard.exec(this._removeFromComparelistImpl.bind(this, e));
    },
    _removeFromComparelistImpl: function (e) {
        var target = $(e.target.closest('.o_comparelist_remove, .o_remove'));
        this.comparelist_product_ids = this.comparelist_product_ids.filter(
            (comp) => comp !== target.data("product_product_id")
        );
        target.parents('.o_product_row').remove();
        this._updateCookie();
        $('.o_comparelist_limit_warning').hide();
        this._updateContent('show');
    },
    /**
     * @private
     */
    _updateCookie: function () {
        cookie.set('comparelist_product_ids', JSON.stringify(this.comparelist_product_ids), 24 * 60 * 60 * 365, 'required');
        this._updateComparelistView();
    },
    /**
     * @private
     */
    _updateComparelistView: function () {
        this.$('.o_product_circle').text(this.comparelist_product_ids.length);
        this.$('.o_comparelist_button').removeClass('d-md-block');
        if (Object.keys(this.comparelist_product_ids || {}).length === 0) {
            $('.o_product_feature_panel').removeClass('d-md-block');
        } else {
            $('.o_product_feature_panel').addClass('d-md-block');
            this.$('.o_comparelist_products').addClass('d-md-block');
            if (this.comparelist_product_ids.length >=2) {
                this.$('.o_comparelist_button').addClass('d-md-block');
                this.$('.o_comparelist_button a').attr('href',
                    '/shop/compare?products=' + encodeURIComponent(this.comparelist_product_ids));
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

publicWidget.registry.ProductComparison = publicWidget.Widget.extend(cartHandlerMixin, {
    selector: '.js_sale',
    events: {
        'click .o_add_compare, .o_add_compare_dyn': '_onClickAddCompare',
        'click #o_comparelist_table tr': '_onClickComparelistTr',
        'submit .o_add_cart_form_compare': '_onFormSubmit',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.productComparison = new ProductComparison(this);
        this.getRedirectOption();
        return Promise.all([def, this.productComparison.appendTo(this.$el)]);
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
    /**
     * @private
     * @param {Event} ev
     */
    _onFormSubmit(ev) {
        ev.preventDefault();
        const $form = $(ev.currentTarget);
        const cellIndex = $(ev.currentTarget).closest('td')[0].cellIndex;
        this.getCartHandlerOptions(ev);
        // Override product image container for animation.
        this.$itemImgContainer = this.$('#o_comparelist_table tr').first().find('td').eq(cellIndex);
        const $inputProduct = $form.find('input[type="hidden"][name="product_id"]').first();
        const productId = parseInt($inputProduct.val());
        if (productId) {
            const productTrackingInfo = $inputProduct.data('product-tracking-info');
            if (productTrackingInfo) {
                productTrackingInfo.quantity = 1;
                $inputProduct.trigger('add_to_cart_event', [productTrackingInfo]);
            }
            return this.addToCart(this._getAddToCartParams(productId, $form));
        }
    },
    /**
     * Get the addToCart Params
     *
     * @param {number} productId
     * @param {JQuery} $form
     * @override
     */
    _getAddToCartParams(productId, $form) {
        return {
            product_id: productId,
            add_qty: 1,
        };
    }
});
export default ProductComparison;
