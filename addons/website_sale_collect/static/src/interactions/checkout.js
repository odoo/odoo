import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { rpc } from '@web/core/network/rpc';
import { Checkout } from '@website_sale/interactions/checkout';

patch(Checkout.prototype, {
     setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '.js_wsc_delete_product': { 't-on-click': this.onClickDeleteProduct.bind(this) },
        });
    },

    /**
     * Remove a product from the cart.
     *
     * @param {Event} ev
     */
    async onClickDeleteProduct(ev) {
        await this.waitFor(rpc('/shop/cart/update', {
            line_id: parseInt(ev.target.dataset.lineId, 10),
            product_id: parseInt(ev.target.dataset.productId, 10),
            quantity: 0,
        }));
        window.location.reload(); // Reload all cart values.
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Remove a warning if available pickup location is selected.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _updatePickupLocation(button, location, jsonLocation) {
        super._updatePickupLocation(...arguments);
        const dmContainer = this._getDeliveryMethodContainer(button);
        const radio = dmContainer.querySelector('[name="o_delivery_radio"]');
        if (radio.dataset.deliveryType === 'in_store') {
            dmContainer.querySelector('[name="unavailable_products_warning"]')?.remove();
        }
    },

    /**
     * Return false if there is a warning message, otherwise return the result of the parent method
     * call.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) { // If there are no delivery methods.
            return super._isDeliveryMethodReady(...arguments); // Skip override.
        }
        const checkedRadio = this.el.querySelector('input[name="o_delivery_radio"]:checked');
        let hasWarning = false;
        if (checkedRadio) {
            const deliveryContainer = this._getDeliveryMethodContainer(checkedRadio);
            hasWarning = (
                checkedRadio.dataset.deliveryType === 'in_store'
                && deliveryContainer.querySelector('[name="unavailable_products_warning"]')
            );
        }
        return super._isDeliveryMethodReady(...arguments) && !hasWarning;
    },

    /**
     * Also hide the warning message, if any.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _hidePickupLocation() {
        super._hidePickupLocation(...arguments);
        const warning = this.el.querySelector('[name="unavailable_products_warning"]');
        if (warning) {
            warning.classList.add('d-none');
        }
    },

    // #=== DELIVERY FLOW ===#

    /**
     * Display a warning if any when selecting an in_store delivery method.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    async _showPickupLocation(radio) {
        super._showPickupLocation(...arguments);
        if (radio.dataset.deliveryType === 'in_store') {
            const dmContainer = this._getDeliveryMethodContainer(radio);
            const warning = dmContainer.querySelector('[name="unavailable_products_warning"]');
            if (warning) {
                warning.classList.remove('d-none');
            }
        }
    },
});
