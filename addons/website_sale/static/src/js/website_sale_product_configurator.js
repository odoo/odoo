/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import wSaleUtils from "@website_sale/js/website_sale_utils";
import { OptionalProductsModal } from "@website_sale/js/sale_product_configurator_modal";
import "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.WebsiteSale.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onProductReady: function () {
        if (this.isBuyNow) {
            return this._submitForm();
        }
        this.optionalProductsModal = new OptionalProductsModal(this.form, {
            rootProduct: this.rootProduct,
            isWebsite: true,
            okButtonText: _t('Proceed to Checkout'),
            cancelButtonText: _t('Continue Shopping'),
            title: _t('Add to cart'),
            context: this._getContext(),
            forceDialog: this.forceDialog,
        }).open();
        this.optionalProductsModal.on('options_empty', null, this._submitForm.bind(this));
        this.optionalProductsModal.on('update_quantity', null, this._onOptionsUpdateQuantity.bind(this));
        this.optionalProductsModal.on('confirm', null, this._onModalSubmit.bind(this, true));
        this.optionalProductsModal.on('back', null, this._onModalSubmit.bind(this, false));

        return this.optionalProductsModal.opened();
    },
    /**
     * Overridden to resolve _opened promise on modal
     * when stayOnPageOption is activated.
     *
     * @override
     */
    _submitForm() {
        var ret = this._super(...arguments);
        if (this.optionalProductsModal && this.stayOnPageOption) {
            ret.then(()=>{
                this.optionalProductsModal._openedResolver()
            });
        }
        return ret;
    },
    /**
     * Update web shop base form quantity
     * when quantity is updated in the optional products window
     *
     * @private
     * @param {integer} quantity
     */
    _onOptionsUpdateQuantity: function (quantity) {
        var qtyInput = this.form.querySelector('.js_main_product input[name="add_qty"]');

        if (qtyInput.length) {
            qtyInput.value = quantity;
            qtyInput.dispatchEvent(new Event('change'));
        } else {
            // This handles the case when the "Select Quantity" customize show
            // is disabled, and therefore the above selector does not find an
            // element.
            // To avoid duplicating all RPC, only trigger the variant change if
            // it is not already done from the above trigger.
            this.optionalProductsModal.triggerVariantChange(this.optionalProductsModal.el);
        }
    },

    /**
     * Submits the form with additional parameters
     * - lang
     * - product_custom_attribute_values: The products custom variant values
     *
     * @private
     * @param {Boolean} goToShop Triggers a page refresh to the url "shop/cart"
     */
    _onModalSubmit: function (goToShop) {
        const mainProduct = this.el.querySelector('.js_product.in_cart.main_product').querySelector('.product_id');
        const productTrackingInfo = mainProduct.dataset.productTrackingInfo;
        if (productTrackingInfo) {
            const currency = productTrackingInfo['currency'];
            const productsTrackingInfo = [];
            this.el.querySelectorAll('.js_product.in_cart').forEach((el) => {
                productsTrackingInfo.push({
                    'item_id': el.getElementsByClassName('product_id').value,
                    'item_name': el.getElementsByClassName('product_display_name').textContent,
                    'quantity': el.getElementsByClassName('js_quantity').value,
                    'currency': currency,
                    'price': el.getElementsByClassName('oe_price').getElementsByClassName('oe_currency_value').teeachxtContent,
                });
            });
            if (productsTrackingInfo) {
                this.el.dispatchEvent(new CustomEvent('add_to_cart_event', { detail: productsTrackingInfo }));
            }
        }

        const callService = this.call.bind(this)
        this.optionalProductsModal.getAndCreateSelectedProducts()
            .then((products) => {
                debugger;
                const productAndOptions = JSON.stringify(products);
                rpc('/shop/cart/update_option', {
                    product_and_options: productAndOptions,
                    ...this._getOptionalCombinationInfoParam(),
                }).then(function (values) {
                    if (goToShop) {
                        window.location.pathname = "/shop/cart";
                    } else {
                        wSaleUtils.updateCartNavBar(values);
                        wSaleUtils.showCartNotification(callService, values.notification_info);
                    }
                }).then(() => {
                    this._getCombinationInfo(document.getElementById('#add_to_cart')?.dispatchEvent(new Event('click')));
                });
            });
    },
});

export default publicWidget.registry.WebsiteSaleOptions;
