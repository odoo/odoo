/** @odoo-module **/

import { Mutex } from "@web/core/utils/concurrency";
import publicWidget from "@web/legacy/js/public/public_widget";
import { cookie } from "@web/core/browser/cookie";;
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import website_sale_utils from "@website_sale/js/website_sale_utils";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
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
    },
    /**
     * @override
     */
    start: function () {
        const self = this;

        self._loadProducts(this.comparelist_product_ids).then(function () {
            self._updateContent('hide');
        });
        self._updateComparelistView();

        new Popover(this.el.querySelector('#comparelist .o_product_header'), {
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
                return this.el.querySelector('#comparelist .o_product_panel_content').innerHTML;
            }
        });
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        window.dispatchEvent(new Event('resize'));

        document.body.addEventListener('click.product_comparaison_widget', '.comparator-popover .o_comparelist_products .o_remove', function (ev) {
            ev.preventDefault();
            self._removeFromComparelist(ev);
        });
        document.body.addEventListener('click.product_comparaison_widget', '.o_comparelist_remove', function (ev) {
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
        document.body.removeEventListener('click.product_comparaison_widget');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Element} elem
     */
    handleCompareAddition: function (elem) {
        const self = this;
        if (this.comparelist_product_ids.length < this.product_compare_limit) {
            let productId = elem.dataset.productProductId;
            if (elem.classList.contains('o_add_compare_dyn')) {
                productId = elem.parentElement.querySelector('.product_id').value;
                if (!productId) { // case List View Variants
                    productId = elem.parentElement.querySelector('input:checked').value;
                }
            }

            let form = elem.closest('form');
            form = form.length ? form : this.el.querySelector('#product_details > form');
            this.selectOrCreateProduct(
                form,
                productId,
                form.querySelector('.product_template_id').value,
            ).then(function (productId) {
                productId = parseInt(productId, 10) || parseInt(elem.dataset.productProductId, 10);
                if (!productId) {
                    return;
                }
                self._addNewProducts(productId).then(function () {
                    website_sale_utils.animateClone(
                        this.el.querySelector('#comparelist .o_product_panel_header'),
                        elem.closest('form'),
                        -50,
                        10
                    );
                });
            });
        } else {
            this.el.querySelector('.o_comparelist_limit_warning').style.display = '';
            new Popover(this.el.querySelector('#comparelist .o_product_panel_header')).show();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _loadProducts: function (product_ids) {
        const self = this;
        const cookies = JSON.parse(cookie.get('comparelist_product_ids') || '[]');
        if (product_ids.length == 0 && cookies.length == 0) {
            return Promise.resolve(true);
        }
        return rpc('/shop/get_product_data', {
            product_ids: product_ids,
            cookies: cookies,
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
        new Popover(this.el.querySelector('#comparelist .o_product_panel_header')).toggle();
    },
    /**
     * @private
     */
    _addNewProducts: function (product_id) {
        return this.guard.exec(this._addNewProductsImpl.bind(this, product_id));
    },
    _addNewProductsImpl: function (product_id) {
        const self = this;
        this.el.querySelectorAll('.o_product_feature_panel').forEach((elem) => elem.classList.add('d-md-block'));
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
        const self = this;
        this.el.querySelectorAll('.o_comparelist_products .o_product_row').forEach((elem) => elem.remove());
        this.comparelist_product_ids.forEach((res) => {
            if (self.product_data.hasOwnProperty(res)) {
                // It is possible that we do not have the required product_data for all IDs in
                // comparelist_product_ids
                const template = self.product_data[res].render;
                self.el.querySelector('.o_comparelist_products').append(template);
            }
        });
        if (force !== 'hide' && (this.comparelist_product_ids.length > 1 || force === 'show')) {
           new Popover(this.el.querySelector('#comparelist .o_product_panel_header')).show();
        }
        else {
            new Popover(this.el.querySelector('#comparelist .o_product_panel_header')).hide();
        }
    },
    /**
     * @private
     */
    _removeFromComparelist: function (e) {
        this.guard.exec(this._removeFromComparelistImpl.bind(this, e));
    },
    _removeFromComparelistImpl: function (e) {
        const target = e.target.closest('.o_comparelist_remove, .o_remove');
        this.comparelist_product_ids = this.comparelist_product_ids.filter(
            (comp) => comp !== target.dataset.productProductId
        );
        // TODO: WAITING FOR MSH PR
        target.parents('.o_product_row').forEach(el => el.remove());
        this._updateCookie();
        this.el.querySelector('.o_comparelist_limit_warning').style.display = 'none';
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
        this.el.querySelector('.o_product_circle').textContent = this.comparelist_product_ids.length;
        this.el.querySelector('.o_comparelist_button').classList.remove('d-md-block');
        if (Object.keys(this.comparelist_product_ids || {}).length === 0) {
            this.el.querySelectorAll('.o_product_feature_panel').forEach(el => el.classList.remove('d-md-block'));
        } else {
            this.el.querySelectorAll('.o_product_feature_panel').forEach(elem => elem.classList.add('d-md-block'));
            this.el.querySelectorAll('.o_comparelist_products').forEach(elem => elem.classList.add('d-md-block'));
            if (this.comparelist_product_ids.length >=2) {
                this.el.querySelector('.o_comparelist_button').classList.add('d-md-block');
                this.el.querySelector('.o_comparelist_button a').
                    setAttribute('href', '/shop/compare?products=' + encodeURIComponent(this.comparelist_product_ids));
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

    /**
     * @override
     */
    start: function () {
        const def = this._super.apply(this, arguments);
        this.productComparison = new ProductComparison(this);
        this.getRedirectOption();
        return Promise.all([def, this.productComparison.appendTo(this.el)]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAddCompare: function (ev) {
        this.productComparison.handleCompareAddition(ev.currentTarget);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickComparelistTr: function (ev) {
        const target = ev.currentTarget;
        // TODO MSH
        $($target.data('target')).children().slideToggle(100);
        target.querySelector('.fa-chevron-circle-down, .fa-chevron-circle-right').forEach(el => {
            el.classList.toggle('fa-chevron-circle-down fa-chevron-circle-right');
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFormSubmit(ev) {
        ev.preventDefault();
        const form = ev.currentTarget;
        const cellIndex = ev.currentTarget.closest('td').cellIndex;
        this.getCartHandlerOptions(ev);
        // Override product image container for animation.
        this.itemImgContainer = this.el.querySelector('#o_comparelist_table tr').children[cellIndex];
        const inputProduct = form.querySelector('input[type="hidden"][name="product_id"]');
        const productId = parseInt(inputProduct.value);
        if (productId) {
            const productTrackingInfo = inputProduct.dataset.productTrackingInfo;
            if (productTrackingInfo) {
                productTrackingInfo.quantity = 1;
                inputProduct.dispatchEvent(new CustomEvent('add_to_cart_event', { detail: [productTrackingInfo] }));
            }
            return this.addToCart(this._getAddToCartParams(productId, form));
        }
    },
    /**
     * Get the addToCart Params
     *
     * @param {number} productId
     * @param {Element} form
     * @override
     */
    _getAddToCartParams(productId, form) {
        return {
            product_id: productId,
            add_qty: 1,
        };
    }
});
export default ProductComparison;
